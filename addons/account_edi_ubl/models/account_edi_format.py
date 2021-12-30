# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
from odoo.tools import float_repr, html2plaintext
from odoo.tests.common import Form

from pathlib import PureWindowsPath

import base64
import logging
import markupsafe

_logger = logging.getLogger(__name__)

def _get_ubl_namespaces(tree):
    """ If the namespace is declared with xmlns='...', the namespaces map contains the 'None' key that causes an
    TypeError: empty namespace prefix is not supported in XPath
    Then, we need to remap arbitrarily this key.

    :param: tree: An instance of etree.
    :return: The namespaces map without 'None' key.
    """
    namespaces = tree.nsmap
    namespaces['inv'] = namespaces.pop(None)
    return namespaces


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    ####################################################
    # Helpers
    ####################################################

    def _is_ubl(self, filename, tree):
        return tree.tag == '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice'

    ####################################################
    # Import
    ####################################################
    def _create_invoice_from_ubl(self, invoice_data):
        # prepare invoice creation context
        move_type = 'out_invoice' if self.env['account.move']._get_default_journal().type == 'sale' else 'in_invoice'
        if invoice_data.get('is_refund'):
            move_type = 'in_refund' if move_type == 'in_invoice' else 'out_refund'
        # The Form object used in `_update_invoice_from_data` will create a new record if the recordSet is empty
        invoice_with_context = self.env['account.move'].with_context(default_move_type=move_type)

        invoice = self._update_invoice_from_data(invoice_with_context, invoice_data)
        if attachments := self._regenerates_pdf_from_datas(invoice, invoice_data):
            invoice.with_context(no_new_invoice=True).message_post(attachment_ids=attachments.ids)

        return invoice

    def _update_invoice_from_ubl(self, invoice, invoice_data):
        # Ensure the move_type isn't changed
        invoice_with_context = invoice.with_context(default_move_type=invoice.move_type)
        invoice = self._update_invoice_from_data(invoice_with_context, invoice_data)
        if attachments := self._regenerates_pdf_from_datas(invoice, invoice_data):
            invoice.with_context(no_new_invoice=True).message_post(attachment_ids=attachments.ids)
        return invoice

    def _retrieve_data_from_ubl_xml(self, tree):
        """
        Retrieve the values from the xml tree and fills it in a dict
        :param namespaces: eventually patched namespace
        :param tree: instance of etree
        :return: dict containing the extracted datas
        """
        namespaces = _get_ubl_namespaces(tree)

        def _find_value(xpath, element=tree):
            return self._find_value(xpath, element, namespaces)

        invoice_data = {}

        # was previously "is not None"
        if (element := tree.find('.//{*}InvoiceTypeCode')) is not None:
            REFUND_CODE = '381'
            invoice_data['is_refund'] = element.text == REFUND_CODE

        # Reference
        if elements := tree.xpath('//cbc:ID', namespaces=namespaces):
            invoice_data['ref'] = elements[0].text
        if elements := tree.xpath('//cbc:InstructionID', namespaces=namespaces):
            invoice_data['payment_reference'] = elements[0].text
        # Dates
        if elements := tree.xpath('//cbc:IssueDate', namespaces=namespaces):
            invoice_data['invoice_date'] = elements[0].text
        if elements := tree.xpath('//cbc:PaymentDueDate', namespaces=namespaces):
            invoice_data['invoice_date_due'] = elements[0].text
        # allow both cbc:PaymentDueDate and cbc:DueDate
        if elements := tree.xpath('//cbc:DueDate', namespaces=namespaces):
            invoice_data['invoice_date_due'] = invoice_data.get('invoice_date_due', elements and elements[0].text)
        # Currency
        if currency := self._retrieve_currency(_find_value('//cbc:DocumentCurrencyCode')):
            invoice_data['currency_id'] = currency
        # Incoterm
        if elements := tree.xpath('//cbc:TransportExecutionTerms/cac:DeliveryTerms/cbc:ID', namespaces=namespaces):
            invoice_data['invoice_incoterm_id'] = self.env['account.incoterms'].search([('code', '=', elements[0].text)], limit=1)
        # Partner
        invoice_data['partner_id'] = self._retrieve_partner(
            name=_find_value('//cac:AccountingSupplierParty/cac:Party//cbc:Name'),
            phone=_find_value('//cac:AccountingSupplierParty/cac:Party//cbc:Telephone'),
            mail=_find_value('//cac:AccountingSupplierParty/cac:Party//cbc:ElectronicMail'),
            vat=_find_value('//cac:AccountingSupplierParty/cac:Party//cbc:CompanyID'),
        )
        # Lines
        lines_elements = tree.xpath('//cac:InvoiceLine', namespaces=namespaces)
        for eline in lines_elements:
            line_data = {}
            invoice_data.setdefault('lines', []).append(line_data)
            # Product
            line_data['product_id'] = self._retrieve_product(
                default_code=_find_value('cac:Item/cac:SellersItemIdentification/cbc:ID', eline),
                name=_find_value('cac:Item/cbc:Name', eline),
                barcode=_find_value('cac:Item/cac:StandardItemIdentification/cbc:ID[@schemeID=\'0160\']', eline)
            )
            # Quantity
            elements = eline.xpath('cbc:InvoicedQuantity', namespaces=namespaces)
            line_data['quantity'] = float(elements[0].text) if elements else 1.0
            # Price Unit
            elements = eline.xpath('cac:Price/cbc:PriceAmount', namespaces=namespaces)
            price_unit = float(elements[0].text) if elements else 0.0
            elements = eline.xpath('cbc:LineExtensionAmount', namespaces=namespaces)
            line_extension_amount = float(elements[0].text) if elements else 0.0
            line_data['price_unit'] = price_unit or line_extension_amount / line_data.get('quantity') or 0.0
            # Name
            elements = eline.xpath('cac:Item/cbc:Description', namespaces=namespaces)
            if elements and elements[0].text:
                line_data['name'] = elements[0].text
                line_data['name'] = line_data['name'].replace('%month%', str(fields.Date.to_date(invoice_data.get('invoice_date')).month))
                line_data['name'] = line_data['name'].replace('%year%', str(fields.Date.to_date(invoice_data.get('invoice_date')).year))
            else:
                partner_name = _find_value('//cac:AccountingSupplierParty/cac:Party//cbc:Name')
                line_data['name'] = "%s (%s)" % (partner_name or '', invoice_data.get('invoice_date'))
            # Taxes
            # TODO: with Benj invoice: 'cac:TaxTotal/cac:TaxSubtotal' don't give any result but 'cac:Item/cac:ClassifiedTaxCategory' does
            tax_element = eline.xpath('cac:TaxTotal/cac:TaxSubtotal', namespaces=namespaces)
            for eline in tax_element:
                # TODO: amount_taxes seems like a weird name: if you have any suggestion to change it: pls give it
                line_data.setdefault('tax_rates', []).append(_find_value('cbc:Percent', eline))

        elements = tree.xpath('//cac:AdditionalDocumentReference', namespaces=namespaces)
        for element in elements:
            attachment_datas = invoice_data.setdefault('attachment_datas', [])
            attachment_name = element.xpath('cbc:ID', namespaces=namespaces)
            attachment_data = element.xpath('cac:Attachment//cbc:EmbeddedDocumentBinaryObject', namespaces=namespaces)
            if attachment_name and attachment_data:
                text = attachment_data[0].text
                # Normalize the name of the file : some e-fff emitters put the full path of the file
                # (Windows or Linux style) and/or the name of the xml instead of the pdf.
                # Get only the filename with a pdf extension.
                name = PureWindowsPath(attachment_name[0].text).stem + '.pdf'
                attachment_vals = {
                    'name': name,
                    'datas': text + '=' * (len(text) % 3),  # Fix incorrect padding
                    'type': 'binary',
                    'mimetype': 'application/pdf',
                }
                attachment_datas.append(attachment_vals)

        return invoice_data

    def _update_invoice_from_data(self, invoice, invoice_data):
        """
        This function update an existing invoice or create an invoice based on data provided by invoice_data
        :param invoice: a record or an empty record of AccountMove
        :param invoice_data: a dict containing the value needed to fill the invoice values
        :return: a record of AccountMove
        """
        invoice_form = Form(invoice.with_context(account_predictive_bills_disable_prediction=True))
        if ref := invoice_data.get('ref'):
            invoice_form.ref = ref
        if payment_reference := invoice_data.get('payment_reference'):
            invoice_form.payment_reference = payment_reference
        if invoice_date := invoice_data.get('invoice_date'):
            invoice_form.invoice_date = invoice_date
        if invoice_date_due := invoice_data.get('invoice_date_due'):
            invoice_form.invoice_date_due = invoice_date_due
        if currency_id := invoice_data.get('currency_id'):
            invoice_form.currency_id = currency_id
        if invoice_incoterm_id := invoice_data.get('invoice_incoterm_id'):
            invoice_form.invoice_incoterm_id = invoice_incoterm_id
        if partner_id := invoice_data.get('partner_id'):
            invoice_form.partner_id = partner_id
        for line_data in invoice_data.get('lines', []):
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                if product_id := line_data.get('product_id'):
                    invoice_line_form.product_id = product_id
                if quantity := line_data.get('quantity'):
                    invoice_line_form.quantity = quantity
                if price_unit := line_data.get('price_unit'):
                    invoice_line_form.price_unit = price_unit
                if name := line_data.get('name'):
                    invoice_line_form.name = name
                invoice_line_form.tax_ids.clear()
                for tax_rate in line_data.get('tax_rates', []):
                    if tax := self._retrieve_tax(amount=tax_rate, type_tax_use=invoice_form.journal_id.type):
                        invoice_line_form.tax_ids.add(tax)
        invoice = invoice_form.save()

        return invoice

    def _regenerates_pdf_from_datas(self, invoice, invoice_data):
        # Regenerate PDF
        attachments = self.env['ir.attachment']
        for attachment_vals in invoice_data.get('attachment_datas', []):
            attachments |= self.env['ir.attachment'].create({
                    'name': attachment_vals.get('name'),
                    'res_id': invoice.id,
                    'res_model': 'account.move',
                    'datas': attachment_vals.get('datas'),
                    'type': attachment_vals.get('type'),
                    'mimetype': attachment_vals.get('mimetype'),
                })
        return attachments

    ####################################################
    # Export
    ####################################################

    def _get_ubl_values(self, invoice):
        ''' Get the necessary values to generate the XML. These values will be used in the qweb template when
        rendering. Needed values differ depending on the implementation of the UBL, as (sub)template can be overriden
        or called dynamically.
        :returns:   a dictionary with the value used in the template has key and the value as value.
        '''
        def format_monetary(amount):
            # Format the monetary values to avoid trailing decimals (e.g. 90.85000000000001).
            return float_repr(amount, invoice.currency_id.decimal_places)

        return {
            **invoice._prepare_edi_vals_to_export(),
            'tax_details': invoice._prepare_edi_tax_details(),
            'ubl_version': 2.1,
            'type_code': 380 if invoice.move_type == 'out_invoice' else 381,
            'payment_means_code': 42 if invoice.journal_id.bank_account_id else 31,
            'bank_account': invoice.partner_bank_id,
            'note': html2plaintext(invoice.narration) if invoice.narration else False,
            'format_monetary': format_monetary,
            'customer_vals': {'partner': invoice.commercial_partner_id},
            'supplier_vals': {'partner': invoice.company_id.partner_id.commercial_partner_id},
        }

    def _export_ubl(self, invoice):
        self.ensure_one()
        # Create file content.
        xml_content = markupsafe.Markup("<?xml version='1.0' encoding='UTF-8'?>")
        xml_content += self.env.ref('account_edi_ubl.export_ubl_invoice')._render(self._get_ubl_values(invoice))
        xml_name = '%s_ubl_2_1.xml' % (invoice.name.replace('/', '_'))
        return self.env['ir.attachment'].create({
            'name': xml_name,
            'raw': xml_content.encode(),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'mimetype': 'application/xml'
        })

    ####################################################
    # Account.edi.format override
    ####################################################

    def _create_invoice_from_xml_tree(self, filename, tree):
        # OVERRIDE
        self.ensure_one()
        if self.code == 'ubl_2_1' and self._is_ubl(filename, tree):
            invoice_data = self._retrieve_data_from_ubl_xml(tree)
            return self._create_invoice_from_ubl(invoice_data)
        return super()._create_invoice_from_xml_tree(filename, tree)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        # OVERRIDE
        self.ensure_one()
        if self.code == 'ubl_2_1' and self._is_ubl(filename, tree):
            invoice_data = self._retrieve_data_from_ubl_xml(tree)
            return self._update_invoice_from_ubl(invoice, invoice_data)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'ubl_2_1':
            return super()._is_compatible_with_journal(journal)
        return journal.type == 'sale'

    def _is_enabled_by_default_on_journal(self, journal):
        # OVERRIDE
        # UBL is disabled by default to prevent conflict with other implementations of UBL.
        self.ensure_one()
        if self.code != 'ubl_2_1':
            return super()._is_enabled_by_default_on_journal(journal)
        return False

    def _post_invoice_edi(self, invoices):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'ubl_2_1':
            return super()._post_invoice_edi(invoices)
        res = {}
        for invoice in invoices:
            attachment = self._export_ubl(invoice)
            res[invoice] = {'success': True, 'attachment': attachment}
        return res
