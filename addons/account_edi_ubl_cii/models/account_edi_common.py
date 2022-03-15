# -*- coding: utf-8 -*-
from lxml import etree

from odoo import _, models
from odoo.tools import float_repr
from zeep import Client
from odoo.exceptions import ValidationError
from odoo.tests.common import Form

FORMAT_CODE_LIST = [
    'facturx_cii',
    'ubl_bis3',
    'ubl_de',
    'ubl_20',
    'ubl_21',
]

#TODO: do it with the xmlid
UOM_TO_UNECE_CODE = {
    'Units': 'C62',
    'Dozens': 'DZN',
    'g': 'GRM',
    'oz': 'ONZ',
    'lb': 'LBR',
    'kg': 'KGM',
    't': 'TNE',
    'Hours': 'HUR',
    'Days': 'DAY',
    'mi': 'SMI',
    'cm': 'CMT',
    'in': 'INH',
    'ft': 'FOT',
    'm': 'MTR',
    'km': 'KTM',
    'in³': 'INQ',
    'fl oz (US)': 'OZA',
    'qt (US)': 'QT',
    'L': 'LTR',
    'gal (US)': 'GLL',
    'ft³': 'FTQ',
    'm³': 'MTQ',
}

COUNTRY_EAS = {
    'HU': 9910,
    'ES': 9920,
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

    'FR': 9957,
}


class AccountEdiCommon(models.AbstractModel):
    _name = "account.edi.common"
    _description = "Common functions for EDI documents: generate the data, the constraints, etc"

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _get_format_code_list(self):
        return FORMAT_CODE_LIST

    def format_float(self, amount, precision_digits):
        if amount is None:
            return None
        return float_repr(amount, precision_digits)

    def _cleanup_xml_content(self, xml_content):
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.fromstring(xml_content, parser=parser)

        def cleanup_node(parent_node, node):
            # Clean children nodes recursively.
            for child_node in node:
                cleanup_node(node, child_node)

            # Remove empty node.
            if parent_node is not None and not len(node) and not (node.text or '').strip():
                parent_node.remove(node)

        cleanup_node(None, tree)

        return etree.tostring(tree, pretty_print=True, encoding='unicode')

    # -------------------------------------------------------------------------
    # ELECTRONIC ADDRESS SCHEME (EAS), see https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/
    # -------------------------------------------------------------------------

    def _get_eas_mapping(self):
        return COUNTRY_EAS

    # -------------------------------------------------------------------------
    # UNIT OF MEASURE
    # -------------------------------------------------------------------------

    def _get_uom_mapping(self):
        return UOM_TO_UNECE_CODE

    def _get_uom_info(self, line):
        # list of codes: https://docs.peppol.eu/poacc/billing/3.0/codelist/UNECERec20/
        # or https://unece.org/fileadmin/DAM/cefact/recommendations/bkup_htm/add2c.htm (sorted by letter)
        # First attempt to cover most cases: convert units to their reference but then
        # Problem: if we buy 1 dozen desks at 1000$/dozen, then in xml, net price per product
        # is marked as 1000$ but quantity is 12 units and lineTotalAmount is 1000$ != 12*1000$ ...
        # Only solution is to have a big dictionary mapping the units and the unit codes
        # If no uom is found -> default to unit = C62
        return UOM_TO_UNECE_CODE.get(line.product_uom_id.name, 'C62')

    # -------------------------------------------------------------------------
    # TAXES
    # -------------------------------------------------------------------------

    def _get_tax_info(self, invoice, tax):
        """
        Source: doc of Peppol (but the CEF norm is also used by factur-x, yet not detailed)
        https://docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice/cac-TaxTotal/cac-TaxSubtotal/cac-TaxCategory/cbc-TaxExemptionReasonCode/
        https://docs.peppol.eu/poacc/billing/3.0/codelist/vatex/
        https://docs.peppol.eu/poacc/billing/3.0/codelist/UNCL5305/
        :returns: (tax_category_code, tax_exemption_reason_code, tax_exemption_reason)
        """
        # TODO: this needs to be improved but no means to say what the tax_reason is
        # if invoice.narration:
        #    if 'VATEX-EU-O' in invoice.narration:
        #        return 'O', 'VATEX-EU-O', 'Not subject to VAT'
        #    if 'VATEX-EU-AE' in invoice.narration:
        #        return 'AE', 'VATEX-EU-AE', 'Reverse charge'
        #    if 'VATEX-EU-D' in invoice.narration:
        #        return 'E', 'VATEX-EU-D', 'Intra-Community acquisition from second hand means of transport'
        #    if 'VATEX-EU-I' in invoice.narration:
        #        return 'E', 'VATEX-EU-I', 'Intra-Community acquisition of works of art'
        #    if 'VATEX-EU-J' in invoice.narration:
        #        return 'E', 'VATEX-EU-J', 'Intra-Community acquisition of collectors items and antiques'
        #    if 'VATEX-EU-F' in invoice.narration:
        #        return 'E', 'VATEX-EU-F', 'Intra-Community acquisition of second hand goods'

        supplier = invoice.company_id.partner_id.commercial_partner_id
        customer = invoice.commercial_partner_id

        # this case raises an error for CII ([BR-IG-08] or [BR-IP-08]) in ecosio but it is okay when I debug it using
        # another validator (create an invoice with a non-null tax with a customer in the canary for instance)...
        if customer.country_id.code == 'ES':
            if customer.zip[:2] in ['35', '38']:  # Canary
                return 'L', None, None  # [BR-IG-10]-A VAT breakdown (BG-23) with VAT Category code (BT-118) "IGIC" shall not have a VAT exemption reason code (BT-121) or VAT exemption reason text (BT-120).
            if customer.zip[:2] in ['51', '52']:
                return 'M', None, None  # Ceuta & Mellila

        if supplier.country_id == customer.country_id:
            if not tax or tax.amount == 0:
                return 'E', None, 'Articles 226 items 11 to 15 Directive 2006/112/EN'  # in theory, you should indicate the precise the article
            else:
                return 'S', None, None  # standard VAT

        if supplier.country_id in self.env.ref('base.europe').country_ids:
            if customer.country_id not in self.env.ref('base.europe').country_ids:
                return 'G', 'VATEX-EU-G', 'Export outside the EU'
            if customer.country_id in self.env.ref('base.europe').country_ids:
                return 'K', 'VATEX-EU-IC', 'Intra-Community supply'

        return None, None, None

    def _get_tax_category_list(self, invoice, taxes):
        """ Full list: https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred5305.htm
        Subset: https://docs.peppol.eu/poacc/billing/3.0/codelist/UNCL5305/

        :param taxes:   account.tax records.
        :return:        A list of values to fill the TaxCategory foreach template.
        """
        res = []
        for tax in taxes:
            category_code, tax_exemption_reason_code, tax_exemption_reason = self._get_tax_info(invoice, tax)
            res.append({
                'id': category_code,
                'percent': tax.amount if tax.amount_type == 'percent' else False,
                'name': tax_exemption_reason,
                'tax_exemption_reason_code': tax_exemption_reason_code,
                'tax_exemption_reason': tax_exemption_reason,
            })
        return res

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    def _check_required_fields(self, record, field_names, custom_warning_message=""):
        """
        This function check that a field exists on a record or dictionaries
        returns a generic error message if it's not the case or a custom one if specified
        """
        if not record:
            return custom_warning_message or _("The element %s is required on %s.", record, ', '.join(field_names))

        if not isinstance(field_names, list):
            field_names = [field_names]

        has_values = any(record[field_name] for field_name in field_names)
        # field is present
        if has_values:
            return

        # field is not present
        if custom_warning_message or isinstance(record, dict):
            return custom_warning_message or _("The element %s is required on %s.", record, ', '.join(field_names))

        display_field_names = record.fields_get(field_names)
        if len(field_names) == 1:
            display_field = f"'{display_field_names[field_names[0]]['string']}'"
            return _("The field %s is required on %s.", display_field, record.display_name)
        else:
            display_fields = ', '.join(f"'{display_field_names[x]['string']}'" for x in display_field_names)
            return _("At least one of the following fields %s is required on %s.", display_fields, record.display_name)

    def _check_constraints(self, constraints):
        return [x for x in constraints.values() if x]

    # -------------------------------------------------------------------------
    # COMMON CONSTRAINTS
    # -------------------------------------------------------------------------

    def _invoice_constraints_common(self, invoice):
        # check that there is at least one tax repartition line !
        for tax in invoice.invoice_line_ids.mapped('tax_ids'):
            for line_repartition_ids in ['invoice_repartition_line_ids', 'refund_repartition_line_ids']:
                lines = tax[line_repartition_ids]
                base_line = lines.filtered(lambda x: x.repartition_type == 'base')
                if not lines - base_line:
                    raise ValidationError(
                        _("Taxes should have at least one tax repartition line."))
        # check that there is a tax on each line
        for line in invoice.invoice_line_ids:
            if not line.tax_ids:
                raise ValidationError(
                    _("Each invoice line should have at least one tax."))

    # -------------------------------------------------------------------------
    # Import invoice
    # -------------------------------------------------------------------------

    def _import_invoice(self, journal, filename, tree, existing_invoice=None):
        move_type, qty_factor = self._import_get_document_type(filename, tree)
        if not move_type or (existing_invoice and existing_invoice.move_type != move_type):
            return

        invoice = existing_invoice or self.env['account.move']
        invoice_form = Form(invoice.with_context(
            account_predictive_bills_disable_prediction=True,
            default_move_type=move_type,
            default_journal_id=journal.id,
        ))
        invoice, logs = self._import_fill_invoice_form(journal, tree, invoice_form, qty_factor)
        if invoice:
            invoice.with_context(no_new_invoice=True).message_post(
                body="<strong>Format used to import the invoice: " + str(self._description) + "</strong>"
                    "<p><li>" + "</li><li>".join(logs) + "</li></p>"
            )
        return invoice

    def _import_fill_invoice_allowance_charge(self, tree, invoice_form, journal, qty_factor):
        logs = []
        if '{urn:oasis:names:specification:ubl:schema:xsd' in tree.tag:
            is_ubl = True
        elif '{urn:un:unece:uncefact:data:standard:' in tree.tag:
            is_ubl = False
        else:
            return

        xpath = './{*}AllowanceCharge' if is_ubl else './{*}SupplyChainTradeTransaction/{*}ApplicableHeaderTradeSettlement/{*}SpecifiedTradeAllowanceCharge'
        allowance_charge_nodes = tree.findall(xpath)
        for allow_el in allowance_charge_nodes:
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.sequence = 0  # be sure to put these lines above the 'real' invoice lines

                charge_factor = -1  # factor is -1 for discount, 1 for charge
                charge_indicator_node = allow_el.find(
                    './{*}ChargeIndicator' if is_ubl else './{*}ChargeIndicator/{*}Indicator')
                if charge_indicator_node is not None:
                    charge_factor = -1 if charge_indicator_node.text == 'false' else 1

                name = ""
                reason_code_node = allow_el.find('./{*}AllowanceChargeReasonCode' if is_ubl else './{*}ReasonCode')
                if reason_code_node is not None:
                    name += reason_code_node.text + " "
                reason_node = allow_el.find('./{*}AllowanceChargeReason' if is_ubl else './{*}Reason')
                if reason_node is not None:
                    name += reason_node.text
                invoice_line_form.name = name

                amount_node = allow_el.find(
                    './{*}Amount' if is_ubl else './{*}ActualAmount')  # net amount, always present
                base_amount_node = allow_el.find(
                    './{*}BaseAmount' if is_ubl else './{*}BasisAmount')  # basis amount, optional
                # Since there is no quantity associated for the allowance/charge on document level,
                # if we have an invoice with negative amounts, the price was multiplied by -1 and not the quantity
                # See the file in test_files: 'base-negative-inv-correction.xml' VS 'base-example.xml' for 'Insurance'
                if base_amount_node is not None:
                    invoice_line_form.price_unit = float(base_amount_node.text) * charge_factor * qty_factor
                    percent_node = allow_el.find('./{*}MultiplierFactorNumeric' if is_ubl else './{*}CalculationPercent')
                    if percent_node is not None:
                        invoice_line_form.quantity = float(percent_node.text) / 100
                elif amount_node is not None:
                    invoice_line_form.price_unit = float(amount_node.text) * charge_factor * qty_factor

                invoice_line_form.tax_ids.clear()  # clear the default taxes applied to the line
                for tax_categ_percent_el in allow_el.findall(
                        './{*}TaxCategory/{*}Percent' if is_ubl else './{*}CategoryTradeTax/{*}RateApplicablePercent'):
                    tax = self.env['account.tax'].search([
                        ('company_id', '=', journal.company_id.id),
                        ('amount', '=', float(tax_categ_percent_el.text)),
                        ('amount_type', '=', 'percent'),
                        ('type_tax_use', '=', 'sale'),
                    ], limit=1)
                    if tax:
                        invoice_line_form.tax_ids.add(tax)
                    else:
                        logs.append(
                            _(f"Could not retrieve the tax: {float(tax_categ_percent_el.text)}% for line '{name}'."))
        return logs

    def _import_fill_invoice_down_payment(self, invoice_form, prepaid_node, qty_factor):
        """
        Creates a down payment line on the invoice at import if prepaid_node (TotalPrepaidAmount in CII,
        PrepaidAmount in UBL) exists.
        qty_factor -1 if the xml is labelled as an invoice but has negative amounts -> conversion into a credit note
        needed, so we need this multiplier. Otherwise, qty_factor is 1.
        """
        if prepaid_node is not None and float(prepaid_node.text) != 0:
            # create a section
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.sequence = 998
                invoice_line_form.display_type = 'line_section'
                invoice_line_form.name = _("Down Payments")
                invoice_line_form.price_unit = 0
                invoice_line_form.quantity = 0
                invoice_line_form.account_id = self.env['account.account']
            # create the line with the down payment
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.sequence = 999
                invoice_line_form.name = _("Down Payment")
                invoice_line_form.price_unit = float(prepaid_node.text)
                invoice_line_form.quantity = qty_factor * -1
                invoice_line_form.tax_ids.clear()

    def _import_fill_invoice_line_values(self, tree, xpath_dict, invoice_line_form, qty_factor):
        """
        Read the xml invoice, extract the invoice line values, compute the odoo values
        to fill an invoice line form: quantity, price_unit, discount, product_uom_id.

        The way of computing invoice line is quite complicated:
        https://docs.peppol.eu/poacc/billing/3.0/bis/#_calculation_on_line_level (same as in factur-x documentation)

        line_net_subtotal = ( gross_unit_price - rebate ) * (billed_qty / basis_qty) - allow_charge_amount

        with (UBL | CII):
            * net_unit_price = 'Price/PriceAmount' | 'NetPriceProductTradePrice' (mandatory) (BT-146)
            * gross_unit_price = 'GrossPriceProductTradePrice' | 'GrossPriceProductTradePrice' (optional) (BT-148)
            * basis_qty = 'Price/BaseQuantity' | 'BasisQuantity' (optional, either below net_price node or
                gross_price node) (BT-149)
            * billed_qty = 'InvoicedQuantity' | 'BilledQuantity' (mandatory) (BT-129)
            * allow_charge_amount = sum of 'AllowanceCharge' | 'SpecifiedTradeAllowanceCharge' (same level as Price)
                ON THE LINE level (optional) (BT-136 / BT-141)
            * line_net_subtotal = 'LineExtensionAmount' | 'LineTotalAmount' (mandatory) (BT-131)
            * rebate = 'Price/AllowanceCharge' | 'AppliedTradeAllowanceCharge' below gross_price node ! (BT-147)
                "item price discount" which is different from the usual allow_charge_amount
                gross_unit_price (BT-148) - rebate (BT-147) = net_unit_price (BT-146)

        In Odoo, we obtain:
        (1) = price_unit  =  gross_price_unit / basis_qty  =  (net_price_unit + rebate) / basis_qty
        (2) = quantity  =  billed_qty
        (3) = discount (converted into a percentage)  =  100 * (1 - price_subtotal / (billed_qty * price_unit))
        (4) = price_subtotal

        Alternatively, we could also set: quantity = billed_qty/basis_qty

        WARNING, the basis quantity parameter is annoying, for instance, an invoice with a line:
            item A  | price per unit of measure/unit price: 30  | uom = 3 pieces | billed qty = 3 | rebate = 2  | untaxed total = 28
        Indeed, 30 $ / 3 pieces = 10 $ / piece => 10 * 3 (billed quantity) - 2 (rebate) = 28

        UBL ROUNDING: "the result of Item line net
            amount = ((Item net price (BT-146)÷Item price base quantity (BT-149))×(Invoiced Quantity (BT-129))
        must be rounded to two decimals, and the allowance/charge amounts are also rounded separately."
        It is not possible to do it in Odoo.

        :params tree
        :params xpath_dict dict: {
            'basis_qty': list of str,
            'gross_price_unit': str,
            'rebate': str,
            'net_price_unit': str,
            'billed_qty': str,
            'allowance_charge': str, to be used in a findall !,
            'allowance_charge_indicator': str, relative xpath from allowance_charge,
            'allowance_charge_amount': str, relative xpath from allowance_charge,
            'line_total_amount': str,
        }
        :params: invoice_line_form
        :params: qty_factor
        """
        # basis_qty (optional)
        basis_qty = 1
        for xpath in xpath_dict['basis_qty']:
            basis_quantity_node = tree.find(xpath)
            if basis_quantity_node is not None:
                basis_qty = float(basis_quantity_node.text)

        # gross_price_unit (optional)
        gross_price_unit = None
        gross_price_unit_node = tree.find(xpath_dict['gross_price_unit'])
        if gross_price_unit_node is not None:
            gross_price_unit = float(gross_price_unit_node.text)

        # rebate (optional)
        # Discount. /!\ as no percent discount can be set on a line, need to infer the percentage
        # from the amount of the actual amount of the discount (the allowance charge)
        rebate = 0
        rebate_node = tree.find(xpath_dict['rebate'])
        net_price_unit_node = tree.find(xpath_dict['net_price_unit'])
        if rebate_node is not None:
            if net_price_unit_node is not None and gross_price_unit_node is not None:
                rebate = float(gross_price_unit_node.text) - float(net_price_unit_node.text)
            else:
                rebate = float(rebate_node.text)

        # net_price_unit (mandatory)
        net_price_unit = None
        if net_price_unit_node is not None:
            net_price_unit = float(net_price_unit_node.text)

        # billed_qty (mandatory)
        billed_qty = 1
        uom_xml = None
        product_uom_id = None
        quantity_node = tree.find(xpath_dict['billed_qty'])
        if quantity_node is not None:
            billed_qty = float(quantity_node.text)
            uom_xml = quantity_node.attrib.get('unitCode')
            if uom_xml:
                uom_infered = [odoo_uom for odoo_uom, uom_unece in self._get_uom_mapping().items() if
                               uom_unece == uom_xml]
                if uom_infered:
                    product_uom_id = self.env['uom.uom'].search([('name', '=', uom_infered[0])], limit=1)

        # allow_charge_amount
        allow_charge_amount = 0  # if positive: it's a discount, if negative: it's a charge
        allow_charge_nodes = tree.findall(xpath_dict['allowance_charge'])
        for allow_charge_el in allow_charge_nodes:
            charge_indicator = allow_charge_el.find(xpath_dict['allowance_charge_indicator'])
            if charge_indicator.text and charge_indicator.text.lower() == 'false':
                discount_factor = 1  # it's a discount
            else:
                discount_factor = -1  # it's a charge
            amount = allow_charge_el.find(xpath_dict['allowance_charge_amount'])
            if amount is not None:
                allow_charge_amount += float(amount.text) * discount_factor

        # line_net_subtotal (mandatory)
        price_subtotal = None
        line_total_amount_node = tree.find(xpath_dict['line_total_amount'])
        if line_total_amount_node is not None:
            price_subtotal = float(line_total_amount_node.text)

        ####################################################
        # Setting the values on the invoice_line_form
        ####################################################

        # quantity
        invoice_line_form.quantity = billed_qty * qty_factor
        if product_uom_id is not None:
            invoice_line_form.product_uom_id = product_uom_id

        # price_unit
        if gross_price_unit is not None:
            price_unit = gross_price_unit / basis_qty
        elif net_price_unit is not None:
            price_unit = (net_price_unit + rebate) / basis_qty
        else:
            raise ValueError("No gross price nor net price found for line in xml")
        invoice_line_form.price_unit = price_unit

        # discount
        if billed_qty * price_unit != 0 and price_subtotal is not None:
            invoice_line_form.discount = 100 * (1 - price_subtotal / (billed_qty * price_unit))

    # -------------------------------------------------------------------------
    # Check xml using the free API from Ph. Helger, don't abuse it !
    # -------------------------------------------------------------------------

    def _check_xml_ecosio(self, invoice, xml_content, xml_formats):
        # see https://peppol.helger.com/public/locale-en_US/menuitem-validation-ws2
        soap_client = Client('https://peppol.helger.com/wsdvs?wsdl')
        if invoice.move_type == 'out_invoice':
            xml_format = xml_formats['invoice']
        elif invoice.move_type == 'out_refund':
            xml_format = xml_formats['credit_note']
        else:
            invoice.with_context(no_new_invoice=True).message_post(
                body="ECOSIO: could not validate xml, formats only exist for invoice or credit notes"
            )
            return
        response = soap_client.service.validate(xml_content, xml_format)
        if not all([item['success'] == 'true' for item in response['Result']]):
            errors = []
            for item in response['Result']:
                if item['artifactPath']:
                    errors.append(
                        "<li><font style='color:Blue;'><strong>" + item['artifactPath'] + "</strong></font></li>")
                for detail in item['Item']:
                    if detail['errorLevel'] == 'WARN':
                        errors.append(
                            "<li><font style='color:Orange;'><strong>" + detail['errorText'] + "</strong></font></li>")
                    else:
                        errors.append(
                            "<li><font style='color:Tomato;'><strong>" + detail['errorText'] + "</strong></font></li>")

            invoice.with_context(no_new_invoice=True).message_post(
                body=f"<font style='color:Tomato;'><strong>ECOSIO ERRORS for format {xml_format}</strong></font>: <ul> "
                     + "\n".join(errors) + " </ul>"
            )
        else:
            invoice.with_context(no_new_invoice=True).message_post(
                body=f"<font style='color:Green;'><strong>ECOSIO: All clear for format {xml_format}!</strong></font>"
            )
        return response
