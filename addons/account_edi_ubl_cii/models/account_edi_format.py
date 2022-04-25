# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
import base64

# this is needed because the account.edi.format codes do not necessarily match
# the suffix of the class used to generate the xml file (and it would be weird to
# rename account.edi.xml.cii into account.edi.xml.facturx_1_0_05 + we would need to change it
# everytime the code of the account.edi.format changes
# TODO: in master, get rid of this by removing old account.edi.formats and creating new ones, with names matching
#  the suffixes
FORMAT_CODE_TO_CLASS_SUFFIX = {
    'facturx_1_0_05': 'cii',
    'ubl_20': 'ubl_20',
    'ubl_2_1': 'ubl_21',
    'ubl_bis3': 'ubl_bis3',
    'ubl_de': 'ubl_de',
    'nlcius_1': 'ubl_nl',
    'ehf_3': 'ubl_no',
}

class AccountEdiFormat(models.Model):
    _name = 'account.edi.format'
    _inherit = 'account.edi.format'

    ####################################################
    # Helpers
    ####################################################

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
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0':
                return self.env['account.edi.xml.ubl_nl']
        if ubl_version is not None:
            if ubl_version.text == '2.0':
                return self.env['account.edi.xml.ubl_20']
            if ubl_version.text == '2.1':
                return self.env['account.edi.xml.ubl_21']
        return

    def _is_generation_possible(self, company):
        """
        Returns a boolean indicating whether it is possible to generate an xml file using one of the formats from this
        module or not
        """
        format_class_suffix = FORMAT_CODE_TO_CLASS_SUFFIX.get(self.code)
        return format_class_suffix and self.env['account.edi.xml.' + format_class_suffix]._get_xml_builder(self.code, company)

    ####################################################
    # Export: Account.edi.format override
    ####################################################

    def _is_required_for_invoice(self, invoice):
        # OVERRIDE
        self.ensure_one()

        if not self._is_generation_possible(invoice.company_id):
            return super()._is_required_for_invoice(invoice)

        if invoice.move_type not in ('out_invoice', 'out_refund'):
            return False
        return True

    def _is_enabled_by_default_on_journal(self, journal):
        # OVERRIDE
        self.ensure_one()

        if self._is_generation_possible(journal.company_id):
            return True

        return super()._is_enabled_by_default_on_journal(journal)

    def _post_invoice_edi(self, invoices, test_mode=False):
        # OVERRIDE
        self.ensure_one()

        if not self._is_generation_possible(invoices[0].company_id):
            return super()._post_invoice_edi(invoices)

        res = {}
        for invoice in invoices:
            format_class_suffix = FORMAT_CODE_TO_CLASS_SUFFIX.get(self.code)
            res = self.env['account.edi.xml.' + format_class_suffix]._get_xml_builder(self.code, invoice.company_id)

            xml_content, errors = res['export_invoice'](invoice)
            # DEBUG: export generated xml file
            #with open(res['invoice_filename'](invoice), 'w+') as f:
            #    f.write(xml_content)
            if errors:
                # don't block the user, but give him a warning in the chatter
                # res[invoice] = {'error': '\n'.join(set(errors))}
                invoice.with_context(no_new_invoice=True).message_post(
                    body=
                    _("Warning, errors occured while creating the edi document (format: %s). The receiver might "
                      "refuse it.", self.env['account.edi.xml.' + format_class_suffix]._description)
                    + '<p> <li>' + "</li> <li>".join(errors) + '</li> <p>'
                )

            # DEBUG: send directly to the test platform (the one used by ecosio)
            #response = self.env['account.edi.common']._check_xml_ecosio(invoice, xml_content, res['ecosio_format'])
            #print("Response: ", response['Result'])

            # remove existing (old) attachments
            self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', invoice.id),
                ('mimetype', '=', 'application/xml'),
                ('name', '=', res['invoice_filename'](invoice)),
            ]).unlink()

            attachment = self.env['ir.attachment'].create({
                'name': res['invoice_filename'](invoice),
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

        if not journal:
            # infer the journal
            journal = self.env['account.journal'].search([
                ('company_id', '=', self.env.company.id), ('type', '=', 'purchase')
            ], limit=1)

        if not self._is_generation_possible(journal.company_id):
            return super()._create_invoice_from_xml_tree(filename, tree, journal=journal)

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

        if not self._is_generation_possible(invoice.company_id):
            return super()._update_invoice_from_xml_tree(filename, tree, invoice)

        # infer the xml builder
        invoice_xml_builder = self._infer_xml_builder_from_tree(tree)

        if invoice_xml_builder is not None:
            invoice = invoice_xml_builder._import_invoice(invoice.journal_id, filename, tree, invoice)
            if invoice:
                return invoice

        return super()._update_invoice_from_xml_tree(filename, tree, invoice)
