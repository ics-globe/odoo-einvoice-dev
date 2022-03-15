# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models, fields
import base64


class AccountEdiFormat(models.Model):
    _name = 'account.edi.format'  # TODO: mandatory to have a _name attribute when inheriting an abstract.model, right ?
    _inherit = [
        'account.edi.format',
        'account.edi.common',
    ]

    ####################################################
    # Helpers
    ####################################################

    def _is_edi_peppol_customer_valid(self, customer):
        return customer.country_id.code in self._get_eas_mapping()

    def _get_edi_peppol_builder(self, company_country_code):
        self.ensure_one()
        if self.code not in self._get_format_code_list():
            return

        if self.code == 'ubl_20':
            return {
                'invoice_xml_builder': self.env['account.edi.xml.ubl_20'],
                'invoice_filename': lambda inv: f"{inv.name.replace('/', '_')}_ubl_20.xml",
                'xml_format': {
                    'invoice': 'org.oasis-open:invoice:2.0',
                    'credit_note': 'org.oasis-open:creditnote:2.0',
                },
                'format_name': "UBL 2.0",
            }

        if self.code == 'ubl_21':
            return {
                'invoice_xml_builder': self.env['account.edi.xml.ubl_21'],
                'invoice_filename': lambda inv: f"{inv.name.replace('/', '_')}_ubl_21.xml",
                'xml_format': {
                    'invoice': 'org.oasis-open:invoice:2.1',
                    'credit_note': 'org.oasis-open:creditnote:2.1',
                },
                'format_name': "UBL 2.1",
            }

        if self.code == 'facturx_cii':
            return {
                # see https://communaute.chorus-pro.gouv.fr/wp-content/uploads/2017/08/20170630_Solution-portail_Dossier_Specifications_Fournisseurs_Chorus_Facture_V.1.pdf
                # page 45 -> ubl 2.1 for France seems also supported
                'invoice_xml_builder': self.env['account.edi.xml.cii'],
                'invoice_filename': lambda inv: "factur-x.xml",
                'xml_format': {
                    'invoice': 'de.xrechnung:cii:2.2.0',
                    'credit_note': 'de.xrechnung:cii:2.2.0',
                },
                'format_name': "Factur-X/XRechnung",
            }

        if self.code == 'ubl_bis3' and company_country_code in self._get_eas_mapping():
            return {
                'invoice_xml_builder': self.env['account.edi.xml.ubl_bis3'],
                'invoice_filename': lambda inv: f"{inv.name.replace('/', '_')}_ubl_bis3.xml",
                'xml_format': {
                    'invoice': 'eu.peppol.bis3:invoice:3.13.0',
                    'credit_note': 'eu.peppol.bis3:creditnote:3.13.0',
                },
                'format_name': "Peppol BIS Billing 3.0",
            }

        if self.code == 'ubl_de' and company_country_code == 'DE':
            return {
                'invoice_xml_builder': self.env['account.edi.xml.ubl_de'],
                'invoice_filename': lambda inv: f"{inv.name.replace('/', '_')}_ubl_de.xml",
                'xml_format': {
                    'invoice': 'de.xrechnung:ubl-invoice:2.2.0',
                    'credit_note': 'de.xrechnung:ubl-creditnote:2.2.0',
                },
                'format_name': "XRechnung",
            }

    def _get_edi_peppol_info(self, company, customer=None):
        self.ensure_one()

        if not company.country_id:
            return
        #if self.code == 'ubl_bis3' and customer is not None and not self._is_edi_peppol_customer_valid(customer):
        #    return

        return self._get_edi_peppol_builder(company.country_id.code.upper())

    def _infer_xml_builder_from_tree(self, tree):
        self.ensure_one()
        ubl_version = tree.find('{*}UBLVersionID')
        customization_id = tree.find('{*}CustomizationID')
        if tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice':
            return self.env['account.edi.xml.cii']
        if customization_id is not None:
            if 'xrechnung' in customization_id.text:
                return self.env['account.edi.xml.ubl_de']
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0':
                return self.env['account.edi.xml.ubl_bis3']
        if ubl_version is not None:
            if ubl_version.text == '2.0':
                return self.env['account.edi.xml.ubl_20']
            if ubl_version.text == '2.1':
                return self.env['account.edi.xml.ubl_21']
        return

    ####################################################
    # Export: Account.edi.format override
    ####################################################

    def _is_required_for_invoice(self, invoice):
        # OVERRIDE
        self.ensure_one()

        if self.code not in self._get_format_code_list():
            return super()._is_required_for_invoice(invoice)

        if invoice.move_type not in ('out_invoice', 'out_refund'):
            return False
        peppol_info = self._get_edi_peppol_info(invoice.company_id, customer=invoice.partner_id)
        return bool(peppol_info)

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        self.ensure_one()

        if self.code not in self._get_format_code_list():
            return super()._is_compatible_with_journal(journal)

        return super()._is_compatible_with_journal(journal)

    def _is_enabled_by_default_on_journal(self, journal):
        # OVERRIDE
        self.ensure_one()

        peppol_info = self._get_edi_peppol_info(journal.company_id)
        if peppol_info:
            return True

        return super()._is_enabled_by_default_on_journal(journal)

    def _post_invoice_edi(self, invoices, test_mode=False):
        # OVERRIDE
        self.ensure_one()

        peppol_info = self._get_edi_peppol_info(invoices.company_id, customer=invoices.partner_id)

        if self.code not in self._get_format_code_list() or not peppol_info:
            return super()._post_invoice_edi(invoices)

        res = {}
        for invoice in invoices:
            xml_content, errors = peppol_info['invoice_xml_builder']._export_invoice(invoice)
            # DEBUG: export generated xml file
            """with open(peppol_info['invoice_filename'](invoice), 'w+') as f:
                f.write(xml_content)"""
            if errors:
                # don't block the user, but give him a warning in the chatter
                # res[invoice] = {'error': '\n'.join(set(errors))}
                invoice.with_context(no_new_invoice=True).message_post(
                    body=_(
                        "Warning, errors occured while creating the edi document (format: %s). "
                        "The receiver might refuse it." % peppol_info['format_name']
                         + '<p> <li>' + "</li> <li>".join(errors) + '</li> <p>'
                    )
                )

            # DEBUG: send directly to the test platform (the one used by ecosio)
            """response = self._check_xml_ecosio(invoice, xml_content, peppol_info['xml_format'])
            print("Response: ", response['Result'])"""

            # remove existing (old) attachments
            self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', invoice.id),
                ('mimetype', '=', 'application/xml'),
                ('name', '=', peppol_info['invoice_filename'](invoice)),
            ]).unlink()

            attachment = self.env['ir.attachment'].create({
                'name': peppol_info['invoice_filename'](invoice),
                'datas': base64.encodebytes(xml_content.encode('utf-8')),
                'res_model': 'account.move',
                'res_id': invoice.id,
                'mimetype': 'application/xml'
            })
            res[invoice] = {'success': True, 'attachment': attachment}

        return res

    def _is_embedding_to_invoice_pdf_needed(self):
        # OVERRIDE
        self.ensure_one()

        if self.code == 'facturx_cii':
            return True
        return super()._is_embedding_to_invoice_pdf_needed()

    ####################################################
    # Import: Account.edi.format override
    ####################################################

    def _create_invoice_from_xml_tree(self, filename, tree, journal=None):
        # OVERRIDE
        self.ensure_one()
        if self.code not in self._get_format_code_list():
            return super()._create_invoice_from_xml_tree(filename, tree, journal=journal)

        invoice_xml_builder = None
        if journal:
            peppol_info = self._get_edi_peppol_info(journal.company_id)
            if peppol_info:
                invoice_xml_builder = peppol_info['invoice_xml_builder']
        else:
            # infer the journal
            journal = self.env['account.journal'].search([
                ('company_id', '=', self.env.company.id), ('type', '=', 'purchase')
            ])
            journal.ensure_one()
            # infer the xml builder
            invoice_xml_builder = self._infer_xml_builder_from_tree(tree)

        if invoice_xml_builder is not None:
            invoice = invoice_xml_builder._import_invoice(journal, filename, tree)
            if invoice:
                return invoice

        return super()._create_invoice_from_xml_tree(filename, tree, journal=journal)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        # OVERRIDE
        self.ensure_one()

        if self.code not in self._get_format_code_list():
            return super()._update_invoice_from_xml_tree(filename, tree, invoice)

        invoice_xml_builder = None
        peppol_info = self._get_edi_peppol_info(invoice.journal_id.company_id)
        if peppol_info:
            invoice_xml_builder = peppol_info['invoice_xml_builder']

        if invoice_xml_builder is not None:
            invoice = invoice_xml_builder._import_invoice(invoice.journal_id, filename, tree, invoice)
            if invoice:
                return invoice

        return super()._update_invoice_from_xml_tree(filename, tree, invoice)
