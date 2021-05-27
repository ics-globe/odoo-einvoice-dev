# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_edi_ubl.models import xml_builder
from odoo import models
from odoo.exceptions import UserError
from odoo.tests.common import Form


COUNTRY_EAS = {
    'HU': 9910,

    'AD': 9922,
    'AL': 9923,
    'BA': 9924,
    'BE': 9925,
    'BG': 9926,
    'CH': 9927,
    'CY': 9928,
    'CZ': 9929,
    'DE': 9930,
    'EE': 9931,
    'UK': 9932,
    'GR': 9933,
    'HR': 9934,
    'IE': 9935,
    'LI': 9936,
    'LT': 9937,
    'LU': 9938,
    'LV': 9939,
    'MC': 9940,
    'ME': 9941,
    'MK': 9942,
    'MT': 9943,
    'NL': 9944,
    'PL': 9945,
    'PT': 9946,
    'RO': 9947,
    'RS': 9948,
    'SI': 9949,
    'SK': 9950,
    'SM': 9951,
    'TR': 9952,
    'VA': 9953,

    'SE': 9955,

    'FR': 9957
}


class AccountEdiFormat(models.Model):
    ''' This edi_format is "abstract" meaning that it provides an additional layer for similar edi_format (formats
    deriving from EN16931) that share some functionalities but needs to be extended to be used.
    '''
    _inherit = 'account.edi.format'

    ####################################################
    # Export
    ####################################################

    def _get_bis3_values(self, invoice):
        values = super()._get_ubl_values(invoice)
        values.update({
            'CustomizationID': 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0',
            'ProfileID': 'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0',
        })

        all_tax_detail_per_tax = {}
        for line_vals in values['invoice_line_vals_list']:
            line_vals['price_subtotal_with_no_tax_closing'] = line_vals['line'].price_subtotal
            tax_detail_per_tax = {}
            for tax_detail_vals in line_vals['tax_detail_vals_list']:
                tax = tax_detail_vals['tax']

                tax_percent = tax.amount
                tax_category = 'S' if tax_percent else 'Z'
                key = (tax_category, tax_percent)
                tax_detail_per_tax.setdefault(key, {
                    'base': tax_detail_vals['tax_base_amount'],
                    'base_currency': tax_detail_vals['tax_base_amount_currency'],
                    'amount': 0.0,
                    'amount_currency': 0.0,
                    'tax_percent': tax_percent,
                    'tax_category': tax_category,
                })
                vals = tax_detail_per_tax[key]

                vals['amount'] += tax_detail_vals['tax_amount_closing']
                vals['amount_currency'] += tax_detail_vals['tax_amount_currency_closing']
                delta_tax = tax_detail_vals['tax_amount_currency'] - tax_detail_vals['tax_amount_currency_closing']
                line_vals['price_subtotal_with_no_tax_closing'] += delta_tax

            if len(tax_detail_per_tax) > 1:
                raise UserError("Multiple vat percentage not supported on the same invoice line")

            line_vals['tax_detail_vals'] = list(tax_detail_per_tax.values())[0]

            for key, tax_vals in tax_detail_per_tax.items():
                all_tax_detail_per_tax.setdefault(key, {
                    **tax_vals,
                    'base': 0.0,
                    'base_currency': 0.0,
                    'amount': 0.0,
                    'amount_currency': 0.0,
                })
                vals = all_tax_detail_per_tax[key]
                vals['base'] += tax_vals['base']
                vals['base_currency'] += tax_vals['base_currency']
                vals['amount'] += tax_vals['amount']
                vals['amount_currency'] += tax_vals['amount_currency']

        values['tax_detail_vals_list'] = list(all_tax_detail_per_tax.values())
        values['total_untaxed_amount'] = sum(x['price_subtotal_with_no_tax_closing'] for x in values['invoice_line_vals_list'])
        values['total_tax_amount'] = sum(x['amount'] for x in values['tax_detail_vals_list'])
        values['total_tax_amount_currency'] = sum(x['amount_currency'] for x in values['tax_detail_vals_list'])

        for partner_vals in (values['customer_vals'], values['supplier_vals']):
            partner = partner_vals['partner']
            if partner.country_id.code in COUNTRY_EAS:
                partner_vals['bis3_endpoint'] = partner.vat
                partner_vals['bis3_endpoint_scheme'] = COUNTRY_EAS[partner.country_id.code]

        return values

    def _bis3_PartyType(self, ubl_PartyType, partner):
        party = ubl_PartyType['cac:Party']
        # TODO this is in ubl as well, maybe we should put it in ubl directly and correct the tests (ubl)
        party.insert_before('cac:PartyName',
            xml_builder.FieldValue('cbc:EndpointID', partner, ['vat'], attrs={'schemeID': str(COUNTRY_EAS[partner.country_id.code])}))

        # TODO This is bis3 only
        del party['cac:Language']
        for tax_scheme in party['cac:PartyTaxScheme']:
            del tax_scheme['cbc:RegistrationName']
            tax_scheme['cac:TaxScheme']['cbc:ID'].attrs = {}  # UBL-DT-27

    def _get_bis3_builder(self, invoice):
        builder = self._get_ubl_2_1_builder(invoice)
        builder.root_node['cbc:CustomizationID'].set_value('urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0')
        builder.root_node['cbc:ProfileID'].set_value('urn:fdc:peppol.eu:2017:poacc:billing:01:1.0')
        del builder.root_node['cbc:UBLVersionID']
        del builder.root_node['cbc:LineCountNumeric']
        builder.root_node.insert_after('cbc:IssueDate',
            xml_builder.FieldValue('cbc:DueDate', invoice, ['invoice_date_due'], value_format=lambda date: date.strftime('%Y-%m-%d')))
        self._bis3_PartyType(builder.root_node['cac:AccountingSupplierParty'], invoice.company_id.partner_id.commercial_partner_id)
        self._bis3_PartyType(builder.root_node['cac:AccountingCustomerParty'], invoice.commercial_partner_id)
        for node in builder.root_node.get_all_items('cac:Country', recursive=True):
            del node['cbc:Name']
        return builder

    ####################################################
    # Import
    ####################################################

    def _bis3_get_extra_partner_domains(self, tree):
        """ Returns an additional domain to find the partner of the invoice based on specific implementation of BIS3.
        TO OVERRIDE

        :returns: a list of domains
        """
        return []

    def _decode_bis3(self, tree, invoice):
        """ Decodes an EN16931 invoice into an invoice.
        :param tree:    the UBL (EN16931) tree to decode.
        :param invoice: the invoice to update or an empty recordset.
        :returns:       the invoice where the UBL (EN16931) data was imported.
        """
        def _find_value(path, root=tree):
            element = root.find(path)
            return element.text if element is not None else None

        element = tree.find('./{*}InvoiceTypeCode')
        if element is not None:
            type_code = element.text
            move_type = 'in_refund' if type_code == '381' else 'in_invoice'
        else:
            move_type = 'in_invoice'

        default_journal = invoice.with_context(default_move_type=move_type)._get_default_journal()

        with Form(invoice.with_context(default_move_type=move_type, default_journal_id=default_journal.id)) as invoice_form:
            # Reference
            element = tree.find('./{*}ID')
            if element is not None:
                invoice_form.ref = element.text

            # Dates
            element = tree.find('./{*}IssueDate')
            if element is not None:
                invoice_form.invoice_date = element.text
            element = tree.find('./{*}DueDate')
            if element is not None:
                invoice_form.invoice_date_due = element.text

            # Currency
            currency = self._retrieve_currency(_find_value('./{*}DocumentCurrencyCode'))
            if currency:
                invoice_form.currency_id = currency

            # Partner
            specific_domain = self._bis3_get_extra_partner_domains(tree)
            invoice_form.partner_id = self._retrieve_partner(
                name=_find_value('./{*}AccountingSupplierParty/{*}Party/*/{*}Name'),
                phone=_find_value('./{*}AccountingSupplierParty/{*}Party/*/{*}Telephone'),
                mail=_find_value('./{*}AccountingSupplierParty/{*}Party/*/{*}ElectronicMail'),
                vat=_find_value('./{*}AccountingSupplierParty/{*}Party/{*}PartyTaxScheme/{*}CompanyID'),
                domain=specific_domain,
            )

            # Lines
            for eline in tree.findall('.//{*}InvoiceLine'):
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    # Product
                    invoice_line_form.product_id = self._retrieve_product(
                        default_code=_find_value('./{*}Item/{*}SellersItemIdentification/{*}ID', eline),
                        name=_find_value('./{*}Item/{*}Name', eline),
                        barcode=_find_value('./{*}Item/{*}StandardItemIdentification/{*}ID[@schemeID=\'0160\']', eline)
                    )

                    # Quantity
                    element = eline.find('./{*}InvoicedQuantity')
                    quantity = element is not None and float(element.text) or 1.0
                    invoice_line_form.quantity = quantity

                    # Price Unit
                    element = eline.find('./{*}Price/{*}PriceAmount')
                    price_unit = element is not None and float(element.text) or 0.0
                    line_extension_amount = element is not None and float(element.text) or 0.0
                    invoice_line_form.price_unit = price_unit or line_extension_amount / invoice_line_form.quantity or 0.0

                    # Name
                    element = eline.find('./{*}Item/{*}Description')
                    invoice_line_form.name = element is not None and element.text or ''

                    # Taxes
                    tax_elements = eline.findall('./{*}Item/{*}ClassifiedTaxCategory')
                    invoice_line_form.tax_ids.clear()
                    for tax_element in tax_elements:
                        invoice_line_form.tax_ids.add(self._retrieve_tax(
                            amount=_find_value('./{*}Percent', tax_element),
                            type_tax_use=invoice_form.journal_id.type
                        ))

        return invoice_form.save()
