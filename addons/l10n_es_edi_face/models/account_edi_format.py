# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from base64 import b64decode
from collections import namedtuple

from lxml import etree

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import file_open, float_repr
from odoo.tools.xml_utils import _check_with_xsd

COUNTRY_CODE_MAP = {
    "BD": "BGD", "BE": "BEL", "BF": "BFA", "BG": "BGR", "BA": "BIH", "BB": "BRB", "WF": "WLF", "BL": "BLM", "BM": "BMU",
    "BN": "BRN", "BO": "BOL", "BH": "BHR", "BI": "BDI", "BJ": "BEN", "BT": "BTN", "JM": "JAM", "BV": "BVT", "BW": "BWA",
    "WS": "WSM", "BQ": "BES", "BR": "BRA", "BS": "BHS", "JE": "JEY", "BY": "BLR", "BZ": "BLZ", "RU": "RUS", "RW": "RWA",
    "RS": "SRB", "TL": "TLS", "RE": "REU", "TM": "TKM", "TJ": "TJK", "RO": "ROU", "TK": "TKL", "GW": "GNB", "GU": "GUM",
    "GT": "GTM", "GS": "SGS", "GR": "GRC", "GQ": "GNQ", "GP": "GLP", "JP": "JPN", "GY": "GUY", "GG": "GGY", "GF": "GUF",
    "GE": "GEO", "GD": "GRD", "GB": "GBR", "GA": "GAB", "SV": "SLV", "GN": "GIN", "GM": "GMB", "GL": "GRL", "GI": "GIB",
    "GH": "GHA", "OM": "OMN", "TN": "TUN", "JO": "JOR", "HR": "HRV", "HT": "HTI", "HU": "HUN", "HK": "HKG", "HN": "HND",
    "HM": "HMD", "VE": "VEN", "PR": "PRI", "PS": "PSE", "PW": "PLW", "PT": "PRT", "SJ": "SJM", "PY": "PRY", "IQ": "IRQ",
    "PA": "PAN", "PF": "PYF", "PG": "PNG", "PE": "PER", "PK": "PAK", "PH": "PHL", "PN": "PCN", "PL": "POL", "PM": "SPM",
    "ZM": "ZMB", "EH": "ESH", "EE": "EST", "EG": "EGY", "ZA": "ZAF", "EC": "ECU", "IT": "ITA", "VN": "VNM", "SB": "SLB",
    "ET": "ETH", "SO": "SOM", "ZW": "ZWE", "SA": "SAU", "ES": "ESP", "ER": "ERI", "ME": "MNE", "MD": "MDA", "MG": "MDG",
    "MF": "MAF", "MA": "MAR", "MC": "MCO", "UZ": "UZB", "MM": "MMR", "ML": "MLI", "MO": "MAC", "MN": "MNG", "MH": "MHL",
    "MK": "MKD", "MU": "MUS", "MT": "MLT", "MW": "MWI", "MV": "MDV", "MQ": "MTQ", "MP": "MNP", "MS": "MSR", "MR": "MRT",
    "IM": "IMN", "UG": "UGA", "TZ": "TZA", "MY": "MYS", "MX": "MEX", "IL": "ISR", "FR": "FRA", "IO": "IOT", "SH": "SHN",
    "FI": "FIN", "FJ": "FJI", "FK": "FLK", "FM": "FSM", "FO": "FRO", "NI": "NIC", "NL": "NLD", "NO": "NOR", "NA": "NAM",
    "VU": "VUT", "NC": "NCL", "NE": "NER", "NF": "NFK", "NG": "NGA", "NZ": "NZL", "NP": "NPL", "NR": "NRU", "NU": "NIU",
    "CK": "COK", "XK": "XKX", "CI": "CIV", "CH": "CHE", "CO": "COL", "CN": "CHN", "CM": "CMR", "CL": "CHL", "CC": "CCK",
    "CA": "CAN", "CG": "COG", "CF": "CAF", "CD": "COD", "CZ": "CZE", "CY": "CYP", "CX": "CXR", "CR": "CRI", "CW": "CUW",
    "CV": "CPV", "CU": "CUB", "SZ": "SWZ", "SY": "SYR", "SX": "SXM", "KG": "KGZ", "KE": "KEN", "SS": "SSD", "SR": "SUR",
    "KI": "KIR", "KH": "KHM", "KN": "KNA", "KM": "COM", "ST": "STP", "SK": "SVK", "KR": "KOR", "SI": "SVN", "KP": "PRK",
    "KW": "KWT", "SN": "SEN", "SM": "SMR", "SL": "SLE", "SC": "SYC", "KZ": "KAZ", "KY": "CYM", "SG": "SGP", "SE": "SWE",
    "SD": "SDN", "DO": "DOM", "DM": "DMA", "DJ": "DJI", "DK": "DNK", "VG": "VGB", "DE": "DEU", "YE": "YEM", "DZ": "DZA",
    "US": "USA", "UY": "URY", "YT": "MYT", "UM": "UMI", "LB": "LBN", "LC": "LCA", "LA": "LAO", "TV": "TUV", "TW": "TWN",
    "TT": "TTO", "TR": "TUR", "LK": "LKA", "LI": "LIE", "LV": "LVA", "TO": "TON", "LT": "LTU", "LU": "LUX", "LR": "LBR",
    "LS": "LSO", "TH": "THA", "TF": "ATF", "TG": "TGO", "TD": "TCD", "TC": "TCA", "LY": "LBY", "VA": "VAT", "VC": "VCT",
    "AE": "ARE", "AD": "AND", "AG": "ATG", "AF": "AFG", "AI": "AIA", "VI": "VIR", "IS": "ISL", "IR": "IRN", "AM": "ARM",
    "AL": "ALB", "AO": "AGO", "AQ": "ATA", "AS": "ASM", "AR": "ARG", "AU": "AUS", "AT": "AUT", "AW": "ABW", "IN": "IND",
    "AX": "ALA", "AZ": "AZE", "IE": "IRL", "ID": "IDN", "UA": "UKR", "QA": "QAT", "MZ": "MOZ"
}
REVERSED_COUNTRY_CODE = {v: k for k, v in COUNTRY_CODE_MAP.items()}

EDI_XML_DICT_TEMPLATES = {
    'business': {
        'TaxIdentification': {},
        'PartyIdentification': False,
        'AdministrativeCentres': [],
        'Assignee': {
            'LegalEntity': False,
            'Individual': False,
        },
    },
    'invoice_line': {
        'IssuerContractReference': False,
        'IssuerContractDate': False,
        'IssuerTransactionReference': False,
        'IssuerTransactionDate': False,
        'ReceiverContractReference': False,
        'ReceiverContractDate': False,
        'ReceiverTransactionReference': False,
        'ReceiverTransactionDate': False,
        'FileReference': False,
        'FileDate': False,
        'SequenceNumber': False,
        'DeliveryNotesReferences': [],
        'ItemDescription': '',
        'Quantity': '',
        'UnitOfMeasure': False,
        'UnitPriceWithoutTax': '',
        'TotalCost': '',
        'DiscountsAndRebates': [],
        'Charges': [],
        'GrossAmount': '',
        'TaxesWitheld': [],
        'TaxesOutputs': [],
        'LineItemPeriod': False,
        'TransactionDate': False,
        'AdditionalLineItemInformation': False,
        'SpecialTaxableEvent': False,
        'ArticleCode': False,
        'Extensions': False,
    },
    'facturae': {
        'Modality': '',
        'InvoiceIssuerType': '',
        'ThirdParty': False,
        'BatchIdentifier': '',
        'InvoicesCount': '',
        'TotalInvoicesAmount': {
            'TotalAmount': '',
            'EquivalentInEuros': False,
        },
        'TotalOutstandingAmount': {
            'TotalAmount': '',
            'EquivalentInEuros': False,
        },
        'TotalExecutableAmount': {
            'TotalAmount': '',
            'EquivalentInEuros': False,
        },
        'InvoiceCurrencyCode': '',
        'FactoringAssignmentData': False,
        'SellerParty': '',
        'BuyerParty': '',
        'Invoices': [],
        'Extensions': False,
    },
    'signature': {
        'SigningTime': '',
        'SignerRole': '',
    },
}


class AccountEdiFaceFormat(models.Model):
    _inherit = 'account.edi.format'

    # ------------------------- #
    #       ES B2G2B EDI        #
    # ------------------------- #

    ################################################
    # Export methods overridden based on EDI Format #
    ################################################

    def _is_compatible_with_journal(self, journal):
        """ Indicate if the EDI format should appear on the journal passed as parameter to be selected by the user.
        If True, this EDI format will appear on the journal.

        :param journal: The journal.
        :returns:       True if this format can appear on the journal, False otherwise.
        """

        if self.code != 'es_face':
            return super()._is_compatible_with_journal(journal)
        self.ensure_one()
        return journal.type == 'sale' and journal.country_code == 'ES'

    def _support_batching(self, move, state, company):
        """ Indicate if we can send multiple documents in the same time to the web services.
        If True, the _post_%s_edi methods will get multiple documents in the same time.
        Otherwise, these methods will be called with only one record at a time.

        :param move:    The move that we are trying to batch.
        :param state:   The EDI state of the move.
        :param company: The company with which we are sending the EDI.
        :returns:       True if batching is supported, False otherwise.
        """
        if self.code != 'es_face':
            return super()._support_batching(move, state, company)
        return False

    def _post_invoice_edi(self, invoices):
        """ Create the file content representing the invoice (and calls web services if necessary).

        :param invoices:    A list of invoices to post.
        :returns:           A dictionary with the invoice as key and as value, another dictionary:
        * success:          True if the edi was successfully posted.
        * attachment:       The attachment representing the invoice in this edi_format.
        * error:            An error if the edi was not successfully posted.
        * blocking_level:   (optional) How bad is the error (how should the edi flow be blocked ?)
        """
        if self.code != 'es_face':
            return super()._post_invoice_edi(invoices)
        res = {}
        for invoice in invoices:
            attachment = self.l10n_es_edi_face_export_facturae(invoice)
            res[invoice] = {'success': True, 'attachment': attachment}
        return res

    def _cancel_invoice_edi(self, invoices):
        """Calls the web services to cancel the invoice of this document.

        :param invoices:    A list of invoices to cancel.
        :returns:           A dictionary with the invoice as key and as value, another dictionary:
        * success:          True if the invoice was successfully cancelled.
        * error:            An error if the edi was not successfully cancelled.
        * blocking_level:   (optional) How bad is the error (how should the edi flow be blocked ?)
        """
        if self.code != 'es_face':
            return super()._cancel_invoice_edi(invoices)
        self.ensure_one()
        return {invoice: {'success': True} for invoice in invoices}  # By default, cancel succeeds doing nothing.

    #############################
    #   EDI SPECIFIC METHODS    #
    #############################

    @staticmethod
    def l10n_es_edi_face_clean_xml(tree_or_str, as_string=True):
        """
        Remove all the unwanted whitespaces and end of lines from the xml tree.
        :param etree.XML or str tree_or_str: the xml tree in etree or str format
        :return: the cleaned xml tree
        """
        str_tree = tree_or_str if isinstance(tree_or_str, str) else etree.tostring(tree_or_str, encoding=str)
        str_tree = re.sub('\n+', '', str_tree)
        str_tree = re.sub(r'\s{2,}', '', str_tree)
        if as_string:
            return str_tree
        return etree.XML(str_tree)

    @staticmethod
    def l10n_es_edi_face_inv_lines_to_items(invoice, conv_rate, needs_equivalency, fmt_in_cur, fmt_in_eur):
        """
        Convert the invoice lines to a list of items required for the FACe xml generation

        :param account.move invoice:    The invoice containing the invoice lines
        :param float conv_rate:         The conversion rate from the invoice currency to the company currency
        :param bool needs_equivalency:  True if the invoice uses multi-currencies
        :param str fmt_in_cur:          The format to use for the amount in the invoice currency
        :param str fmt_in_eur:          The format to use for the amount in euros
        :return tuple:                  A tuple containing the Face items, the taxes and the invoice totals data.
        """

        def compute_tax_amount(tax, line):
            return tax.amount if tax.amount_type == 'fixed' else line.price_subtotal * tax.amount / 100.

        items = []
        totals = {
            'total_gross_amount': 0.,
            'total_general_discounts': 0.,
            'total_general_surcharges': 0.,
            'total_taxes_withheld': 0.,
            'total_payments_on_account': 0.,
            'amounts_withheld': 0.,
        }
        taxes = []
        for line in invoice.invoice_line_ids:
            invoice_line_values = EDI_XML_DICT_TEMPLATES['invoice_line'].copy()

            total_price = line.quantity * line.price_unit * conv_rate  # This isn't a mistake
            gross_amount = line.price_subtotal / conv_rate
            discount = max(0., line.discount * total_price)
            surcharge = max(0., - line.discount * total_price)  # + line.price_total - line.price_subtotal
            totals['total_gross_amount'] += gross_amount
            totals['total_general_discounts'] += discount
            totals['total_general_surcharges'] += surcharge

            taxes_output = [{
                "TaxTypeCode": tax.l10n_es_edi_face_tax_type,
                "TaxRate": f'{tax.amount :.3f}' if tax.amount_type == 'percent' else '0.000',
                "TaxableBase": {
                    'TotalAmount': fmt_in_cur(gross_amount),
                    'EquivalentInEuros': fmt_in_eur(line.price_subtotal) if needs_equivalency else False,
                },  # TODO Improve the tax amount computation
                "TaxAmount": {
                    "TotalAmount": fmt_in_cur(
                            compute_tax_amount(tax, line) / conv_rate
                    ),
                    "EquivalentInEuros": fmt_in_eur(compute_tax_amount(tax, line)),
                },
            } for tax in line.tax_ids]

            invoice_line_values.update({
                'ItemDescription': line.name,
                'Quantity': line.quantity,
                'UnitOfMeasure': line.product_uom_id.l10n_es_edi_face_uom_code,
                'UnitPriceWithoutTax': fmt_in_cur(line.price_unit),
                'TotalCost': fmt_in_cur(total_price),
                'DiscountsAndRebates': [{
                    'DiscountReason': '',
                    'DiscountRate': f'{line.discount:.2f}',
                    'DiscountAmount': fmt_in_cur(discount)
                },
                ] if discount != 0. else [],
                'Charges': [{
                    'ChargeReason': '',
                    'ChargeRate': f'{max(0, -line.discount):.2f}',
                    'ChargeAmount': fmt_in_cur(surcharge)
                },
                ] if surcharge != 0. else [],
                'GrossAmount': fmt_in_cur(gross_amount),
                'TaxesOutputs': taxes_output,
            })
            items.append(invoice_line_values)
            taxes += taxes_output
        return items, taxes, totals

    def l10n_es_edi_face_export_facturae(self, invoice):
        """
        Produce the Facturae XML file for the invoice.

        :param account.move invoice: The invoice to export.
        :return ir.attachment: The attachment containing the XML file.
        """

        self.ensure_one()

        self_company = invoice.company_id
        partner = invoice.partner_id.parent_id or invoice.partner_id

        if not self_company.l10n_es_edi_face_tax_identifier:
            raise UserError(_('The company needs a set tax identification number or VAT number'))

        if not partner.l10n_es_edi_face_tax_identifier:
            raise UserError(_('The partner needs a set tax identification number or VAT number'))

        def format_in_euro(value):
            # Format the monetary values to avoid trailing decimals (e.g. 90.850...1).
            return float_repr(value, euro_currency.decimal_places)

        def format_in_currency(number):
            # Format the monetary values to avoid trailing decimals (e.g. 90.850...1).
            if invoice_currency.name == 'EUR':
                return format_in_euro(number)
            return float_repr(number, invoice_currency.decimal_places)

        euro_currency = self.env['res.currency'].search([('name', '=', 'EUR')])
        invoice_currency = invoice.currency_id or self_company.currency_id
        IndividualName = namedtuple('IndividualName', ['firstname', 'surname', 'surname2'])
        firstname = surname = surname2 = ''
        phone_clean_table = str.maketrans({" ": None, "-": None, "(": None, ")": None, "+": None})
        legal_literals = invoice.narration.striptags() if invoice.narration else False
        legal_literals = legal_literals.split(";") if legal_literals else False

        if partner.is_company:
            partner_name = IndividualName('', '', '')
        else:
            name_split = [part for part in partner.name.replace(',', ' ').split(' ') if part]
            if len(name_split) > 2:
                firstname = ' '.join(name_split[:-2])
                surname, surname2 = name_split[-2:]
            elif len(name_split) == 2:
                firstname = ' '.join(name_split[:-1])
                surname = name_split[-1]

            partner_name = IndividualName(firstname, surname, surname2)

        template_values = EDI_XML_DICT_TEMPLATES['facturae'].copy()
        self_party_values = EDI_XML_DICT_TEMPLATES['business'].copy()
        partner_party_values = EDI_XML_DICT_TEMPLATES['business'].copy()
        signature_values = EDI_XML_DICT_TEMPLATES['signature'].copy()

        if invoice.move_type == "entry":
            return False
        invoice_issuer_type = 'EM' if invoice.move_type == 'out_invoice' else 'RE'
        invoice_issuer_signature_type = 'supplier' if invoice.move_type == 'out_invoice' else 'customer'

        company_is_not_euro = self_company.currency_id != euro_currency
        invoice_is_not_euro = invoice_currency != euro_currency

        if not (company_is_not_euro or invoice_is_not_euro):
            conversion_rate = 1.00
            needs_equivalency = False

        elif not company_is_not_euro and invoice_is_not_euro:
            conversion_rate = invoice.amount_total_signed / invoice.amount_total_in_currency_signed
            needs_equivalency = True

        elif company_is_not_euro and invoice_is_not_euro:
            conversion_rate = invoice_currency.with_context(date=invoice.date_invoice).rate
            conversion_rate /= euro_currency.with_context(date=invoice.date_invoice).rate
            needs_equivalency = True

        else:
            conversion_rate = 1.00
            needs_equivalency = False

        total_outst_am_in_currency = abs(invoice.amount_total_in_currency_signed)
        total_outst_am = invoice.amount_total

        total_exec_am_in_currency = abs(invoice.amount_total_in_currency_signed)
        total_exec_am = invoice.amount_total

        self_party_values.update({
            'TaxIdentification': {
                'PersonTypeCode': self_company.l10n_es_edi_face_person_type,
                'ResidenceTypeCode': self_company.l10n_es_edi_face_residence_type,
                'TaxIdentificationNumber': self_company.l10n_es_edi_face_tax_identifier,
            },
            'Assignee': {
                'LegalEntity': {
                    'CorporateName': self_company.name,
                    'TradeName': self_company.display_name,
                    'address': {
                        'Address': ', '.join([val for val in (partner.street, partner.street2) if val]),
                        'PostCode': self_company.zip,
                        'Town': self_company.city,
                        'Province': self_company.state_id.name if self_company.state_id else
                        self_company.country_id.name,
                        'CountryCode': COUNTRY_CODE_MAP[self_company.country_id.code],
                    },
                    'ContactDetails': {
                        'Telephone': self_company.phone.translate(phone_clean_table) if self_company.phone else False,
                        'WebAdress': self_company.website if self_company.email else False,
                        'ElectronicMail': self_company.email if self_company.email else False,
                    },
                } if self_company.l10n_es_edi_face_person_type == 'J' else False,
            },
        })
        partner_party_values.update({
            'TaxIdentification': {
                'PersonTypeCode': partner.l10n_es_edi_face_person_type,
                'ResidenceTypeCode': partner.l10n_es_edi_face_residence_type,
                'TaxIdentificationNumber': partner.l10n_es_edi_face_tax_identifier,
            },
            'Assignee': {
                'LegalEntity': {
                    'CorporateName': partner.name,
                    'TradeName': partner.display_name,
                    'address': {
                        'Address': ', '.join([val for val in (partner.street, partner.street2) if val]),
                        'PostCode': partner.zip,
                        'Town': partner.city,
                        'Province': partner.state_id.name if partner.state_id else partner.country_id.name,
                        'CountryCode': COUNTRY_CODE_MAP[partner.country_id.code],
                    },
                    'ContactDetails': {
                        'Telephone': partner.phone.translate(phone_clean_table) if partner.phone else False,
                        'WebAdress': partner.website if partner.website else False,
                        'ElectronicMail': partner.email if partner.email else False,
                    },
                } if partner.l10n_es_edi_face_person_type == 'J' else False,
                'Individual': {
                    'Name': partner_name.firstname,
                    'FirstSurname': partner_name.surname,
                    'SecondSurname': partner_name.surname2,
                    'address': {
                        'Address': ', '.join([val for val in (partner.street, partner.street2) if val]),
                        'PostCode': partner.zip,
                        'Town': partner.city,
                        'Province': partner.state_id.name if partner.state_id else partner.country_id.name,
                        'CountryCode': COUNTRY_CODE_MAP[partner.country_id.code],
                    },
                    'ContactDetails': {
                        'Telephone': partner.phone.translate(phone_clean_table) if partner.phone else False,
                        'WebAdress': partner.website if partner.website else False,
                        'ElectronicMail': partner.email if partner.email else False,
                    },
                } if partner.l10n_es_edi_face_person_type == 'F' else False,
            },
        })

        items, taxes, totals = self.l10n_es_edi_face_inv_lines_to_items(invoice, conversion_rate, needs_equivalency,
                                                                        format_in_currency, format_in_euro)

        template_values.update({
            'Modality': 'I',
            'InvoiceIssuerType': invoice_issuer_type,
            'BatchIdentifier': invoice.name,
            'InvoicesCount': 1,
            'TotalInvoicesAmount': {
                'TotalAmount': format_in_currency(abs(invoice.amount_total_in_currency_signed)),
                'EquivalentInEuros': format_in_euro(invoice.amount_total) if needs_equivalency else False,
            },
            'TotalOutstandingAmount': {
                'TotalAmount': format_in_currency(total_outst_am_in_currency),
                'EquivalentInEuros': format_in_euro(total_outst_am) if needs_equivalency else False,
            },
            'TotalExecutableAmount': {
                'TotalAmount': format_in_currency(total_exec_am_in_currency),
                'EquivalentInEuros': format_in_euro(total_exec_am) if needs_equivalency else False,
            },
            'InvoiceCurrencyCode': invoice_currency.name,
            'SellerParty': self_party_values if invoice.move_type == 'out_invoice' else partner_party_values,
            'BuyerParty': self_party_values if invoice.move_type == 'in_invoice' else partner_party_values,
            'Invoices': [{
                'InvoiceNumber': invoice.name,
                'InvoiceDocumentType': 'FC',
                'InvoiceClass': 'OO',
                'InvoiceIssueData': {
                    'IssueDate': invoice.invoice_date,
                    'InvoiceCurrencyCode': invoice_currency.name,
                    'ExchangeRateDetails': needs_equivalency,
                    'ExchangeRate': f'{conversion_rate:.2f}',
                    'ExchangeDate': invoice.date,
                    'TaxCurrencyCode': invoice_currency.name,
                    'LanguageName': self._context.get('lang', 'en_US').split('_')[0],
                },
                'TaxOutputs': taxes,
                'TaxesWithheld': [],
                'TotalGrossAmount': format_in_currency(totals['total_gross_amount']),
                'TotalGeneralDiscounts': format_in_currency(totals['total_general_discounts']),
                'TotalGeneralSurcharges': format_in_currency(totals['total_general_surcharges']),
                'TotalGrossAmountBeforeTaxes': format_in_currency(abs(invoice.amount_untaxed_signed) / conversion_rate),
                'TotalTaxOutputs': format_in_currency(
                        abs(invoice.amount_total_in_currency_signed - invoice.amount_untaxed_signed) / conversion_rate
                ),
                'TotalTaxesWithheld': format_in_currency(totals['total_taxes_withheld']),
                'PaymentsOnAccount': [],
                'TotalOutstandingAmount': format_in_currency(total_outst_am_in_currency),
                'InvoiceTotal': format_in_currency(abs(invoice.amount_total_in_currency_signed)),
                'TotalPaymentsOnAccount': format_in_currency(totals['total_payments_on_account']),
                'AmountsWithheld': {
                    'WithholdingReason': '',
                    'WithholdingRate': False,
                    'WithouldingAmount': format_in_currency(totals['amounts_withheld']),
                } if totals['amounts_withheld'] else False,
                'TotalExecutableAmount': format_in_currency(total_exec_am_in_currency),
                'PaymentInKind': False,
                'Items': items,
                'PaymentDetails': [],
                'LegalLiterals': legal_literals,
                'AdditionalData': {
                    'RelatedInvoice': False,
                    'RelatedDocuments': [],
                    'Extensions': False,
                },
            }],
        })
        signature_values.update({
            'SignerRole': invoice_issuer_signature_type,
        })

        xml_content = self.env['ir.qweb']._render('l10n_es_edi_face.account_invoice_facturae_export', template_values)
        signed = False
        try:
            certificate = self.env['l10n_es_edi_face.certificate'].search([("company_id", '=', self_company.id)])[0]
            xml_content = certificate.sign_xml(xml_content, signature_values)
            signed = True
        except IndexError:
            nspaces = {'ds': 'http://www.w3.org/2000/09/xmldsig#', 'etsi': 'http://uri.etsi.org/01903/v1.4.1#'}
            xml_tree = etree.fromstring(xml_content.encode("utf-8"))
            signature = xml_tree.xpath('.//ds:Signature', namespaces=nspaces)[0]
            xml_tree.remove(signature)
            xml_content = etree.tostring(xml_tree, pretty_print=True, encoding='utf-8', xml_declaration=True,
                                         standalone=True)
            raise UserError(_('No valid certificate found for this company, FACe EDI file will not be signed.\n'))
        xml_name = f'{invoice.name.replace("/", "_")}_FACE_{"un" if signed else ""}signed.xml'
        with file_open('l10n_es_edi_face/data/Facturaev3_2_2.xsd', 'rb') as xsd:
            try:
                _check_with_xsd(xml_content, xsd)
            except UserError as e:  # Hack-fix for error when certificate serial is bigger than the integer limit
                if not re.match(
                        r"\<string\>:[0-9]+:0:ERROR:SCHEMASV:SCHEMAV_CVC_DATATYPE_VALID_1_2_1: Element \'\{"
                        r"http://www\.w3\.org/2000/09/xmldsig#\}X509SerialNumber\': \'[0-9]+\' is not a valid value "
                        r"of the atomic type \'xs:integer\'\.", e.args[0]):
                    raise e from e
        return self.env['ir.attachment'].create({
            'name': xml_name,
            'raw': xml_content,
            'res_model': 'account.edi.document',
            'mimetype': 'application/xml'
        })
