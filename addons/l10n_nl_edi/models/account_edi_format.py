# -*- coding: utf-8 -*-

from odoo.addons.account_edi_ubl.models import xml_builder
from odoo import models, _

import base64


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    ####################################################
    # Import
    ####################################################

    def _is_ubl(self, filename, tree):
        """ OVERRIDE so that the generic ubl parser does not parse BIS3 any longer.
        """
        is_ubl = super()._is_ubl(filename, tree)
        return is_ubl and not self._is_nlcius(filename, tree)

    def _is_nlcius(self, filename, tree):
        profile_id = tree.find('./{*}ProfileID')
        customization_id = tree.find('./{*}CustomizationID')
        return tree.tag == '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice' and \
            profile_id is not None and 'peppol' in profile_id.text and \
            customization_id is not None and 'nlcius' in customization_id.text

    def _bis3_get_extra_partner_domains(self, tree):
        if self.code == 'nlcius_1':
            endpoint = tree.find('./{*}AccountingSupplierParty/{*}Party/{*}EndpointID')
            if endpoint is not None:
                scheme = endpoint.attrib['schemeID']
                if scheme == '0106' and endpoint.text:
                    return [('l10n_nl_kvk', '=', endpoint.text)]
                elif scheme == '0190' and endpoint.text:
                    return [('l10n_nl_oin', '=', endpoint.text)]
        return []

    ####################################################
    # Export
    ####################################################

    def _get_nlcius_values(self, invoice):
        values = super()._get_bis3_values(invoice)
        values.update({
            'CustomizationID': 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0',
            'payment_means_code': 30,
        })

        for partner_vals in (values['customer_vals'], values['supplier_vals']):
            partner = partner_vals['partner']
            endpoint = partner.l10n_nl_oin or partner.l10n_nl_kvk
            if partner.country_code == 'NL' and endpoint:
                scheme = '0190' if partner.l10n_nl_oin else '0106'
                partner_vals.update({
                    'bis3_endpoint': endpoint,
                    'bis3_endpoint_scheme': scheme,
                    'legal_entity': endpoint,
                    'legal_entity_scheme': scheme,
                    'partner_identification': endpoint,
                })

        return values

    def _nlcius_PartyType(self, accounting_party, partner):
        accounting_party['cac:Party'].insert_after('cac:PartyTaxScheme',
            xml_builder.Parent('cbc:PartyLegalEntity', [
                xml_builder.FieldValue(
                    'cbc:RegistrationName',
                    partner,
                    ['name']
                ),
                xml_builder.FieldValue(
                    'cbc:CompanyID',
                    partner,
                    ['l10n_nl_oin', 'l10n_nl_kvk'],
                    attrs={'schemeID': '0190' if partner.l10n_nl_oin else '0106'},
                ),
            ])
        )

        if partner.country_code == 'NL':
            endpoint_node = accounting_party['cac:Party']['cbc:EndpointID']
            endpoint_node.fieldnames = ['l10n_nl_oin', 'l10n_nl_kvk']
            endpoint_node.attrs = {'schemeID': '0190' if partner.l10n_nl_oin else '0106'}

            accounting_party['cac:Party'].insert_after('cbc:EndpointID',
            xml_builder.Parent('cac:PartyIdentification', [
                xml_builder.FieldValue('cbc:ID', partner, ['l10n_nl_oin', 'l10n_nl_kvk'])
            ]))

    def _get_nlcius_builder(self, invoice):
        builder = self._get_bis3_builder(invoice)
        builder.root_node['cbc:CustomizationID'].set_value('urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0')
        self._nlcius_PartyType(builder.root_node['cac:AccountingSupplierParty'], invoice.company_id.partner_id.commercial_partner_id)
        self._nlcius_PartyType(builder.root_node['cac:AccountingCustomerParty'], invoice.commercial_partner_id)
        return builder

    def _export_nlcius(self, invoice):
        self.ensure_one()
        # Create file content.
        # xml_content = b"<?xml version='1.0' encoding='UTF-8'?>"
        # xml_content += self.env.ref('l10n_nl_edi.export_nlcius_invoice')._render(self._get_nlcius_values(invoice))
        builder = self.env['account.edi.format']._get_nlcius_builder(invoice)
        xml_content = builder.build()
        vat = invoice.company_id.partner_id.commercial_partner_id.vat
        xml_name = 'nlcius-%s%s%s.xml' % (vat or '', '-' if vat else '', invoice.name.replace('/', '_'))
        return self.env['ir.attachment'].create({
            'name': xml_name,
            'datas': base64.encodebytes(xml_content),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'mimetype': 'application/xml'
        })

    ####################################################
    # Account.edi.format override
    ####################################################

    def _check_move_configuration(self, invoice):
        res = super()._check_move_configuration(invoice)
        if self.code != 'nlcius_1':
            return res

        errors = []

        supplier = invoice.company_id.partner_id.commercial_partner_id
        if not supplier.street or not supplier.zip or not supplier.city:
            errors.append(_("The supplier's address must include street, zip and city (%s).", supplier.display_name))
        if supplier.country_code == 'NL' and not supplier.l10n_nl_kvk and not supplier.l10n_nl_oin:
            errors.append(_("The supplier %s must have a KvK-nummer or OIN.", supplier.display_name))
        if not supplier.vat:
            errors.append(_("Please define a VAT number for '%s'.", supplier.display_name))

        customer = invoice.commercial_partner_id
        if customer.country_code == 'NL' and (not customer.street or not customer.zip or not customer.city):
            errors.append(_("Customer's address must include street, zip and city (%s).", customer.display_name))
        if customer.country_code == 'NL' and not customer.l10n_nl_kvk and not customer.l10n_nl_oin:
            errors.append(_("The customer %s must have a KvK-nummer or OIN.", customer.display_name))

        if not invoice.partner_bank_id:
            errors.append(_("The supplier %s must have a bank account.", supplier.display_name))

        if invoice.invoice_line_ids.filtered(lambda l: not (l.product_id.name or l.name)):
            errors.append(_('Each invoice line must have a product or a label.'))

        if invoice.invoice_line_ids.tax_ids.invoice_repartition_line_ids.filtered(lambda r: r.use_in_tax_closing) and \
           not supplier.vat:
            errors.append(_("When vat is present, the supplier must have a vat number."))

        return errors

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        if self.code != 'nlcius_1':
            return super()._is_compatible_with_journal(journal)
        return journal.type == 'sale' and journal.country_code == 'NL'

    def _post_invoice_edi(self, invoices):
        self.ensure_one()
        if self.code != 'nlcius_1':
            return super()._post_invoice_edi(invoices)

        invoice = invoices  # no batch ensure that there is only one invoice
        attachment = self._export_nlcius(invoice)
        return {invoice: {'attachment': attachment}}

    def _is_embedding_to_invoice_pdf_needed(self):
        self.ensure_one()
        if self.code != 'nlcius_1':
            return super()._is_embedding_to_invoice_pdf_needed()
        return False

    def _create_invoice_from_xml_tree(self, filename, tree):
        self.ensure_one()
        if self.code == 'nlcius_1' and self._is_nlcius(filename, tree):
            return self._decode_bis3(tree, self.env['account.move'])
        return super()._create_invoice_from_xml_tree(filename, tree)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self.code == 'nlcius_1' and self._is_nlcius(filename, tree):
            return self._decode_bis3(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)
