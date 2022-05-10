# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_repr, is_html_empty, html2plaintext

from datetime import datetime

import logging

_logger = logging.getLogger(__name__)

DEFAULT_FACTURX_DATE_FORMAT = '%Y%m%d'


class AccountEdiXmlCII(models.AbstractModel):
    _name = "account.edi.xml.cii"
    _inherit = 'account.edi.common'
    _description = "Factur-x/XRechnung CII 2.2.0"

    def _get_xml_builder(self, format_code, company):
        # see https://communaute.chorus-pro.gouv.fr/wp-content/uploads/2017/08/20170630_Solution-portail_Dossier_Specifications_Fournisseurs_Chorus_Facture_V.1.pdf
        # page 45 -> ubl 2.1 for France seems also supported
        if format_code == 'facturx_1_0_05':
            return {
                'export_invoice': self._export_invoice,
                'invoice_filename': lambda inv: "factur-x.xml",
                'ecosio_format': {
                    'invoice': 'de.xrechnung:cii:2.2.0',
                    'credit_note': 'de.xrechnung:cii:2.2.0',
                },
            }

    def _export_invoice_constraints(self, invoice, vals):
        constraints = self._invoice_constraints_common(invoice)
        constraints.update({
            # [BR-08]-An Invoice shall contain the Seller postal address (BG-5).
            # [BR-09]-The Seller postal address (BG-5) shall contain a Seller country code (BT-40).
            'seller_postal_address': self._check_required_fields(
                vals['record']['company_id']['partner_id']['commercial_partner_id'], 'country_id'
            ),
            # [BR-DE-9] The element "Buyer post code" (BT-53) must be transmitted. (only mandatory in Germany ?)
            'buyer_postal_address': self._check_required_fields(
                vals['record']['commercial_partner_id'], 'zip'
            ),
            # [BR-DE-4] The element "Seller post code" (BT-38) must be transmitted. (only mandatory in Germany ?)
            'seller_post_code': self._check_required_fields(
                vals['record']['company_id']['partner_id']['commercial_partner_id'], 'zip'
            ),
            # [BR-CO-26]-In order for the buyer to automatically identify a supplier, the Seller identifier (BT-29),
            # the Seller legal registration identifier (BT-30) and/or the Seller VAT identifier (BT-31) shall be present.
            'seller_identifier': self._check_required_fields(
                vals['record']['company_id'], ['vat']  # 'siret'
            ),
            # [BR-DE-1] An Invoice must contain information on "PAYMENT INSTRUCTIONS" (BG-16)
            # first check that a partner_bank_id exists, then check that there is an account number
            'seller_payment_instructions_1': self._check_required_fields(
                vals['record'], 'partner_bank_id'
            ),
            'seller_payment_instructions_2': self._check_required_fields(
                vals['record']['partner_bank_id'], 'sanitized_acc_number',
                _("The field 'Sanitized Account Number' is required on the Recipient Bank.")
            ),
            # [BR-DE-15] The element "Buyer reference" (BT-10) must be transmitted
            # (required only for certain buyers in France when using Chorus pro, it's the "service executant")
            #TODO: should we enforce this ? annoying to always have the warning while it's not always necessary
            # alternatively, we could just send a custom message like "In some cases, this field is required [...]"
            #'buyer_reference': self._check_required_fields(
            #    vals['record']['commercial_partner_id'], 'ref'
            #),
            # [BR-DE-6] The element "Seller contact telephone number" (BT-42) must be transmitted.
            'seller_phone': self._check_required_fields(
                vals['record']['company_id']['partner_id']['commercial_partner_id'], ['phone', 'mobile'],
            ),
            # [BR-DE-7] The element "Seller contact email address" (BT-43) must be transmitted.
            'seller_email': self._check_required_fields(
                vals['record']['company_id'], 'email'
            ),
            # [BR-CO-04]-Each Invoice line (BG-25) shall be categorized with an Invoiced item VAT category code (BT-151).
            'tax_invoice_line': self._check_required_tax(vals),
            # [BR-IC-02]-An Invoice that contains an Invoice line (BG-25) where the Invoiced item VAT category code (BT-151)
            # is "Intra-community supply" shall contain the Seller VAT Identifier (BT-31) or the Seller tax representative
            # VAT identifier (BT-63) and the Buyer VAT identifier (BT-48).
            'intracom_seller_vat': self._check_required_fields(vals['record']['company_id'], 'vat') if vals['intracom_delivery'] else None,
            'intracom_buyer_vat': self._check_required_fields(vals['record']['commercial_partner_id'], 'vat') if vals['intracom_delivery'] else None,
            # [BR-IG-05]-In an Invoice line (BG-25) where the Invoiced item VAT category code (BT-151) is "IGIC" the
            # invoiced item VAT rate (BT-152) shall be greater than 0 (zero).
            'igic_tax_rate': self._check_non_0_rate_tax(vals)
                if vals['record']['commercial_partner_id']['country_id']['code'] == 'ES'
                   and vals['record']['commercial_partner_id']['zip'][:2] in ['35', '38'] else None,
        })
        return constraints

    def _check_required_tax(self, vals):
        for line_vals in vals['invoice_line_vals_list']:
            line = line_vals['line']
            if not vals['tax_details']['invoice_line_tax_details'][line]['tax_details']:
                return _("You should include at least one tax per invoice line. [BR-CO-04]-Each Invoice line (BG-25) "
                         "shall be categorized with an Invoiced item VAT category code (BT-151).")

    def _check_non_0_rate_tax(self, vals):
        for line_vals in vals['invoice_line_vals_list']:
            tax_rate_list = line_vals['line'].tax_ids.mapped("amount")
            if not any([rate > 0 for rate in tax_rate_list]):
                return _("When the Canary Island General Indirect Tax (IGIC) applies, the tax rate on "
                         "each invoice line should be greater than 0.")

    def _get_scheduled_delivery_time(self, invoice):
        # don't create a bridge only to get line.sale_line_ids.order_id.picking_ids.date_done
        # line.sale_line_ids.order_id.picking_ids.scheduled_date or line.sale_line_ids.order_id.commitment_date
        return invoice.invoice_date

    def _get_invoicing_period(self, invoice):
        # get the Invoicing period (BG-14): a list of dates covered by the invoice
        # don't create a bridge to get the date range from the timesheet_ids
        return [invoice.invoice_date]

    def _get_exchanged_document_vals(self, invoice):
        return {
            'id': invoice.name,
            'type_code': '381' if 'refund' in invoice.move_type else '380',
            'issue_date_time': invoice.invoice_date,
            'included_note': html2plaintext(invoice.narration) if invoice.narration else "",
        }

    def _export_invoice_vals(self, invoice):

        def format_date(dt):
            # Format the date in the Factur-x standard.
            dt = dt or datetime.now()
            return dt.strftime(DEFAULT_FACTURX_DATE_FORMAT)

        def format_monetary(number, decimal_places=2):
            # Facturx requires the monetary values to be rounded to 2 decimal values
            return float_repr(number, decimal_places)

        # Create file content.
        tax_details = invoice._prepare_edi_tax_details()
        balance_sign = -1 if invoice.is_inbound() else 1

        seller_siret = 'siret' in invoice.company_id._fields and invoice.company_id.siret or invoice.company_id.company_registry
        buyer_siret = 'siret' in invoice.commercial_partner_id._fields and invoice.commercial_partner_id.siret

        template_values = {
            **invoice._prepare_edi_vals_to_export(),
            'tax_details': tax_details,
            'format_date': format_date,
            'format_monetary': format_monetary,
            'is_html_empty': is_html_empty,
            'scheduled_delivery_time': self._get_scheduled_delivery_time(invoice),
            'intracom_delivery': False,
            'ExchangedDocument_vals': self._get_exchanged_document_vals(invoice),
            'seller_specified_legal_organization': seller_siret,
            'buyer_specified_legal_organization': buyer_siret,
        }

        # data used for IncludedSupplyChainTradeLineItem / SpecifiedLineTradeSettlement
        for line_vals in template_values['invoice_line_vals_list']:
            line = line_vals['line']
            line_vals['unece_uom_code'] = self._get_uom_unece_code(line)
            # data used for IncludedSupplyChainTradeLineItem / SpecifiedLineTradeSettlement / ApplicableTradeTax
            for tax_detail_vals in template_values['tax_details']['invoice_line_tax_details'][line]['tax_details'].values():
                tax = tax_detail_vals['tax']
                tax_detail_vals['unece_tax_category_code'] = self._get_tax_unece_codes(invoice, tax)[0]
                tax_detail_vals['amount_type'] = tax.amount_type
                tax_detail_vals['amount'] = tax.amount

        # data used for ApplicableHeaderTradeSettlement / ApplicableTradeTax (at the end of the xml)
        for tax_detail_vals in template_values['tax_details']['tax_details'].values():
            tax = tax_detail_vals['tax']
            tax_detail_vals['amount_type'] = tax.amount_type
            tax_detail_vals['amount'] = tax.amount
            # /!\ -0.0 == 0.0 in python but not in XSLT, so it can raise a fatal error when validating the XML
            # if 0.0 is expected and -0.0 is given.
            amount_currency = tax_detail_vals['tax_amount_currency']
            tax_detail_vals['calculated_amount'] = balance_sign * amount_currency if amount_currency != 0 else 0
            tax_category_code, tax_exemption_reason_code, tax_exemption_reason = self._get_tax_unece_codes(invoice, tax)
            tax_detail_vals['unece_tax_category_code'] = tax_category_code
            tax_detail_vals['exemption_reason'] = tax_exemption_reason
            tax_detail_vals['exemption_reason_code'] = tax_exemption_reason_code

            if tax_category_code == 'K':
                template_values['intracom_delivery'] = True
            # [BR - IC - 11] - In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Actual delivery date (BT-72) or the Invoicing period (BG-14) shall not be blank.
            if tax_category_code == 'K' and not template_values['scheduled_delivery_time']:
                date_range = self._get_invoicing_period(invoice)
                template_values['billing_start'] = min(date_range)
                template_values['billing_end'] = max(date_range)

        # TODO: One of the difference between XRechnung and Facturx is the following. Submitting a Facturx to XRechnung
        #   validator raises a warning, but submitting a XRechnung to Facturx raises an error. Thus, it's safer
        #   to always use the french tag
        #supplier = invoice.company_id.partner_id.commercial_partner_id
        #if supplier.country_id.code == 'DE':
        #    template_values['document_context_id'] = "urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_2.2"
        template_values['document_context_id'] = "urn:cen.eu:en16931:2017"

        return template_values

    def _export_invoice(self, invoice):
        vals = self._export_invoice_vals(invoice)
        template = self.env.ref('account_edi_ubl_cii.account_invoice_facturx_export_22')
        errors = self._check_constraints(self._export_invoice_constraints(invoice, vals))
        return self._cleanup_xml_content(template._render(vals)), set(errors)

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_fill_invoice_form(self, journal, tree, invoice_form, qty_factor):

        def _find_value(xpath, element=tree):
            return self.env['account.edi.format']._find_value(xpath, element, tree.nsmap)

        logs = []

        if qty_factor == -1:
            logs.append(_("The invoice has been converted into a credit note and the quantities have been reverted."))

        # ==== partner_id ====

        partner_type = invoice_form.journal_id.type == 'purchase' and 'SellerTradeParty' or 'BuyerTradeParty'
        invoice_form.partner_id = self.env['account.edi.format']._retrieve_partner(
            name=_find_value(f"//ram:{partner_type}/ram:Name"),
            mail=_find_value(f"//ram:{partner_type}//ram:URIID[@schemeID='SMTP']"),
            vat=_find_value(f"//ram:{partner_type}/ram:SpecifiedTaxRegistration/ram:ID"),
        )
        if not invoice_form.partner_id:
            logs.append(_("Could not retrieve the vendor."))

        # ==== currency_id ====

        currency_code_node = tree.find('.//{*}InvoiceCurrencyCode')
        if currency_code_node is not None:
            currency = self.env['res.currency'].with_context(active_test=False).search([
                ('name', '=', currency_code_node.text),
            ], limit=1)
            if currency:
                if not currency.active:
                    logs.append(_("The currency '%s' is not active.", currency.name))
                invoice_form.currency_id = currency
            else:
                logs.append(_("Could not retrieve currency: %s. Did you enable the multicurrency option and "
                              "activate the currency ?", currency_code_node.text))

        # ==== Reference ====

        ref_node = tree.find('./{*}ExchangedDocument/{*}ID')
        if ref_node is not None:
            invoice_form.ref = ref_node.text

        # === Note/narration ====

        narration = ""
        note_node = tree.find('./{*}ExchangedDocument/{*}IncludedNote/{*}Content')
        if note_node is not None:
            narration += note_node.text + "\n"

        payment_terms_node = tree.find('.//{*}SpecifiedTradePaymentTerms/{*}Description')
        if payment_terms_node is not None:
            narration += payment_terms_node.text + "\n"

        invoice_form.narration = narration

        # ==== payment_reference ====

        payment_reference_node = tree.find('.//{*}BuyerOrderReferencedDocument/{*}IssuerAssignedID')
        if payment_reference_node is not None:
            invoice_form.payment_reference = payment_reference_node.text

        # ==== invoice_date ====

        invoice_date_node = tree.find('./{*}ExchangedDocument/{*}IssueDateTime/{*}DateTimeString')
        if invoice_date_node is not None:
            date_str = invoice_date_node.text
            date_obj = datetime.strptime(date_str, DEFAULT_FACTURX_DATE_FORMAT)
            invoice_form.invoice_date = date_obj.strftime(DEFAULT_SERVER_DATE_FORMAT)

        # ==== invoice_date_due ====

        invoice_date_due_node = tree.find('.//{*}SpecifiedTradePaymentTerms/{*}DueDateDateTime/{*}DateTimeString')
        if invoice_date_due_node is not None:
            date_str = invoice_date_due_node.text
            date_obj = datetime.strptime(date_str, DEFAULT_FACTURX_DATE_FORMAT)
            invoice_form.invoice_date_due = date_obj.strftime(DEFAULT_SERVER_DATE_FORMAT)

        # ==== invoice_line_ids: AllowanceCharge (document level) ====

        logs += self._import_fill_invoice_allowance_charge(tree, invoice_form, journal, qty_factor)

        # ==== Down Payment (prepaid amount) ====

        prepaid_node = tree.find('.//{*}ApplicableHeaderTradeSettlement/'
                                 '{*}SpecifiedTradeSettlementHeaderMonetarySummation/{*}TotalPrepaidAmount')
        self._import_fill_invoice_down_payment(invoice_form, prepaid_node, qty_factor)

        # ==== invoice_line_ids ====

        line_nodes = tree.findall('./{*}SupplyChainTradeTransaction/{*}IncludedSupplyChainTradeLineItem')
        if line_nodes is not None:
            for i, invl_el in enumerate(line_nodes):
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    invoice_line_form.sequence = i
                    invl_logs = self._import_fill_invoice_line_form(journal, invl_el, invoice_form, invoice_line_form, qty_factor)
                    logs += invl_logs

        return invoice_form, logs

    def _import_fill_invoice_line_form(self, journal, tree, invoice_form, invoice_line_form, qty_factor):
        logs = []

        def _find_value(xpath, element=tree):
            return self.env['account.edi.format']._find_value(xpath, element, tree.nsmap)

        # Product.
        name = _find_value('.//ram:SpecifiedTradeProduct/ram:Name', tree)
        if name:
            invoice_line_form.name = name
        invoice_line_form.product_id = self.env['account.edi.format']._retrieve_product(
            default_code=_find_value('.//ram:SpecifiedTradeProduct/ram:SellerAssignedID', tree),
            name=_find_value('.//ram:SpecifiedTradeProduct/ram:Name', tree),
            barcode=_find_value('.//ram:SpecifiedTradeProduct/ram:GlobalID', tree)
        )

        xpath_dict = {
            'basis_qty': [
                './{*}SpecifiedLineTradeAgreement/{*}GrossPriceProductTradePrice/{*}BasisQuantity',
                './{*}SpecifiedLineTradeAgreement/{*}NetPriceProductTradePrice/{*}BasisQuantity'
            ],
            'gross_price_unit': './{*}SpecifiedLineTradeAgreement/{*}GrossPriceProductTradePrice/{*}ChargeAmount',
            'rebate': './{*}SpecifiedLineTradeAgreement/{*}GrossPriceProductTradePrice/{*}AppliedTradeAllowanceCharge/{*}ActualAmount',
            'net_price_unit': './{*}SpecifiedLineTradeAgreement/{*}NetPriceProductTradePrice/{*}ChargeAmount',
            'billed_qty': './{*}SpecifiedLineTradeDelivery/{*}BilledQuantity',
            'allowance_charge': './/{*}SpecifiedLineTradeSettlement/{*}SpecifiedTradeAllowanceCharge',
            'allowance_charge_indicator': './{*}ChargeIndicator/{*}Indicator',  # below allowance_charge node
            'allowance_charge_amount': './{*}ActualAmount',  # below allowance_charge node
            'line_total_amount': './{*}SpecifiedLineTradeSettlement/{*}SpecifiedTradeSettlementLineMonetarySummation/{*}LineTotalAmount',
        }
        self._import_fill_invoice_line_values(tree, xpath_dict, invoice_line_form, qty_factor)

        if not invoice_line_form.product_uom_id:
            logs.append(
                _("Could not retrieve the unit of measure for line with label '%s'. Did you install the inventory "
                  "app and enabled the 'Units of Measure' option ?", invoice_line_form.name))

        # Taxes
        taxes = []
        tax_nodes = tree.findall('.//{*}ApplicableTradeTax/{*}RateApplicablePercent')
        for tax_node in tax_nodes:
            tax = self.env['account.tax'].search([
                ('company_id', '=', journal.company_id.id),
                ('amount', '=', float(tax_node.text)),
                ('amount_type', '=', 'percent'),
                ('type_tax_use', '=', 'sale'),
            ], limit=1)
            if tax:
                taxes.append(tax)
            else:
                logs.append(
                    _("Could not retrieve the tax: %s %% for line '%s'.", float(tax_node.text), invoice_line_form.name))

        invoice_line_form.tax_ids.clear()
        for tax in taxes:
            invoice_line_form.tax_ids.add(tax)
        return logs

    # -------------------------------------------------------------------------
    # IMPORT : helpers
    # -------------------------------------------------------------------------

    def _import_get_document_type(self, filename, tree):
        """
        In factur-x, an invoice has code 380 and a credit note has code 381. However, a credit note can be expressed
        as an invoice with negative amounts. For this case, we need a factor to take the opposite of each quantity
        in the invoice.
        """
        move_type_code = tree.find('.//{*}ExchangedDocument/{*}TypeCode')
        if move_type_code is None:
            return None, None
        if move_type_code.text == '381':
            return 'in_refund', 1
        if move_type_code.text == '380':
            amount_node = tree.find('.//{*}SpecifiedTradeSettlementHeaderMonetarySummation/{*}TaxBasisTotalAmount')
            if amount_node is not None and float(amount_node.text) < 0:
                return 'in_refund', -1
            return 'in_invoice', 1
