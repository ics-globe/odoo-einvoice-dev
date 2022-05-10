# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import ValidationError

from stdnum.no import mva


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _name = "account.edi.xml.ubl_bis3"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL BIS Billing 3.0.12"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _get_xml_builder(self, format_code, company):
        # if a the company country is not in the EAS mapping, nothing is generated
        if format_code == 'ubl_bis3' and company.country_id.code in self.env['account.edi.common']._get_eas_mapping():
            return {
                'export_invoice': self._export_invoice,
                'invoice_filename': lambda inv: f"{inv.name.replace('/', '_')}_ubl_bis3.xml",
                'ecosio_format': {
                    'invoice': 'eu.peppol.bis3:invoice:3.13.0',
                    'credit_note': 'eu.peppol.bis3:creditnote:3.13.0',
                },
            }

    def _get_country_vals(self, country):
        # OVERRIDE
        vals = super()._get_country_vals(country)

        vals.pop('name', None)

        return vals

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # OVERRIDE
        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)

        for vals in vals_list:
            vals.pop('registration_name', None)
            vals.pop('RegistrationAddress_vals', None)

        # sources:
        #  https://anskaffelser.dev/postaward/g3/spec/current/billing-3.0/norway/#_applying_foretaksregisteret
        #  https://docs.peppol.eu/poacc/billing/3.0/bis/#national_rules (NO-R-002 (warning))
        if partner.country_id.code == "NO" and role == 'supplier':
            vals_list.append({
                'company_id': "Foretaksregisteret",
                'tax_scheme_id': "TAX",
            })

        return vals_list

    def _get_partner_party_legal_entity_vals_list(self, partner):
        # OVERRIDE
        vals_list = super()._get_partner_party_legal_entity_vals_list(partner)

        for vals in vals_list:
            vals.pop('RegistrationAddress_vals', None)
            if partner.country_code == 'NL':
                endpoint = partner.l10n_nl_oin or partner.l10n_nl_kvk
                scheme = '0190' if partner.l10n_nl_oin else '0106'
                vals.update({
                    'company_id': endpoint,
                    'company_id_attrs': {'schemeID': scheme},
                })

        return vals_list

    def _get_partner_contact_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_contact_vals(partner)

        vals.pop('id', None)

        return vals

    def _get_partner_party_vals(self, partner, role):
        # OVERRIDE
        vals = super()._get_partner_party_vals(partner, role)

        vals['endpoint_id'] = partner.vat
        vals['endpoint_id_attrs'] = {'schemeID': self._get_eas_mapping().get(partner.country_id.code)}

        if partner.country_code == 'NO' and 'l10n_no_bronnoysund_number' in partner._fields:
            vals.update({
                'endpoint_id': partner.l10n_no_bronnoysund_number,
                'endpoint_id_attrs': {'schemeID': '0192'},
            })
        # [BR-NL-1] Dutch supplier registration number ( AccountingSupplierParty/Party/PartyLegalEntity/CompanyID );
        # With a Dutch supplier (NL), SchemeID may only contain 106 (Chamber of Commerce number) or 190 (OIN number).
        # [BR-NL-10] At a Dutch supplier, for a Dutch customer ( AccountingCustomerParty ) the customer registration
        # number must be filled with Chamber of Commerce or OIN. SchemeID may only contain 106 (Chamber of
        # Commerce number) or 190 (OIN number).
        if partner.country_code == 'NL' and ('l10n_nl_oin' in partner._fields or 'l10n_nl_kvk' in partner._fields):
            endpoint = partner.l10n_nl_oin or partner.l10n_nl_kvk
            scheme = '0190' if partner.l10n_nl_oin else '0106'
            vals.update({
                'endpoint_id': endpoint,
                'endpoint_id_attrs': {'schemeID': scheme},
            })

        return vals

    def _get_partner_party_identification_vals_list(self, partner):
        # OVERRIDE
        vals = super()._get_partner_party_identification_vals_list(partner)

        if partner.country_code == 'NL':
            endpoint = partner.l10n_nl_oin or partner.l10n_nl_kvk
            vals.append({
                'id': endpoint,
                'id_attrs': None,
            })
        return vals

    def _get_delivery_vals_list(self, invoice):
        # OVERRIDE
        supplier = invoice.company_id.partner_id.commercial_partner_id
        customer = invoice.commercial_partner_id

        economic_area = self.env.ref('base.europe').country_ids.mapped('code') + ['NO']
        intracom_delivery = (customer.country_id.code in economic_area
                             and supplier.country_id.code in economic_area
                             and supplier.country_id != customer.country_id)

        if not intracom_delivery:
            return []

        # [BR-IC-12]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
        # "Intra-community supply" the Deliver to country code (BT-80) shall not be blank.

        # [BR-IC-11]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
        # "Intra-community supply" the Actual delivery date (BT-72) or the Invoicing period (BG-14)
        # shall not be blank.

        if 'partner_shipping_id' in invoice._fields:
            partner_shipping = invoice.partner_shipping_id
        elif partner_id := invoice._get_invoice_delivery_partner_id():
            partner_shipping = self.env['res.partner'].browse(partner_id)
        else:
            partner_shipping = customer

        return [{
            'actual_delivery_date': invoice.invoice_date,
            'Location_vals': {
                'DeliveryAddress_vals': self._get_partner_address_vals(partner_shipping),
            },
        }]

    def _get_partner_address_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_address_vals(partner)
        # schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt
        # [UBL-CR-225]-A UBL invoice should not include the AccountingCustomerParty Party PostalAddress CountrySubentityCode
        vals.pop('country_subentity_code', None)
        return vals

    def _get_financial_institution_branch_vals(self, bank):
        # OVERRIDE
        vals = super()._get_financial_institution_branch_vals(bank)
        # schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt
        # [UBL-CR-664]-A UBL invoice should not include the FinancialInstitutionBranch FinancialInstitution
        # xpath test: not(//cac:FinancialInstitution)
        vals.pop('id_attrs', None)
        vals.pop('FinancialInstitution_vals', None)
        return vals

    def _get_invoice_payment_means_vals_list(self, invoice):
        # OVERRIDE
        vals_list = super()._get_invoice_payment_means_vals_list(invoice)

        for vals in vals_list:
            vals.pop('payment_due_date', None)
            vals.pop('instruction_id', None)
            if vals.get('payment_id_vals'):
                vals['payment_id_vals'] = vals['payment_id_vals'][:1]

        return vals_list

    def _get_tax_category_list(self, invoice, taxes):
        # OVERRIDE
        vals_list = super()._get_tax_category_list(invoice, taxes)

        for vals in vals_list:
            vals.pop('name')
            # [UBL-CR-601]-A UBL invoice should not include the InvoiceLine Item ClassifiedTaxCategory TaxExemptionReason
            #vals.pop('tax_exemption_reason')

        return vals_list

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # OVERRIDE
        vals_list = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)

        for vals in vals_list:
            vals['currency_dp'] = 2
            for subtotal_vals in vals.get('TaxSubtotal_vals', []):
                subtotal_vals.pop('percent', None)
                subtotal_vals['currency_dp'] = 2

        return vals_list

    def _get_invoice_line_allowance_vals_list(self, line):
        # OVERRIDE
        vals_list = super()._get_invoice_line_allowance_vals_list(line)

        for vals in vals_list:
            vals['currency_dp'] = 2

        return vals_list

    def _get_invoice_line_vals(self, line, taxes_vals):
        # OVERRIDE
        vals = super()._get_invoice_line_vals(line, taxes_vals)

        vals.pop('TaxTotal_vals', None)

        vals['currency_dp'] = 2
        vals['Price_vals']['currency_dp'] = 2

        return vals

    def _export_invoice_vals(self, invoice):
        # OVERRIDE
        vals = super()._export_invoice_vals(invoice)

        #vals['PartyType_template'] = 'account_edi_ubl_cii.ubl_bis3_PartyType'

        vals['vals'].update({
            'customization_id': 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0',
            'profile_id': 'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0',
            'currency_dp': 2,
        })
        vals['vals']['LegalMonetaryTotal_vals']['currency_dp'] = 2

        # [NL-R-001] For suppliers in the Netherlands, if the document is a creditnote, the document MUST
        # contain an invoice reference (cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID)
        if vals['supplier'].country_id.code == 'NL' and 'refund' in invoice.move_type:
            vals['vals'].update({
                'BillingReference_vals': {
                    'id': invoice.ref,
                    'issue_date': None,
                }
            })

        return vals

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals)
        constraints.update(
            self._invoice_constraints_peppol_en16931_ubl(invoice, vals)
        )
        constraints.update(
            self._invoice_constraints_cen_en16931_ubl(invoice, vals)
        )

        return constraints

    def _invoice_constraints_cen_en16931_ubl(self, invoice, vals):
        """
        corresponds to the errors raised by ' schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt' for invoices.
        This xslt was obtained by transforming the corresponding sch
        https://docs.peppol.eu/poacc/billing/3.0/files/CEN-EN16931-UBL.sch.
        """
        intracom_delivery = (vals['customer'].country_id in self.env.ref('base.europe').country_ids
                             and vals['supplier'].country_id in self.env.ref('base.europe').country_ids
                             and vals['customer'].country_id != vals['supplier'].country_id)

        constraints = {
            # [BR-S-02]-An Invoice that contains an Invoice line (BG-25) where the Invoiced item VAT category code
            # (BT-151) is "Standard rated" shall contain the Seller VAT Identifier (BT-31), the Seller tax registration
            # identifier (BT-32) and/or the Seller tax representative VAT identifier (BT-63).
            # ---
            # [BR-CO-26]-In order for the buyer to automatically identify a supplier, the Seller identifier (BT-29),
            # the Seller legal registration identifier (BT-30) and/or the Seller VAT identifier (BT-31) shall be present.
            'cen_en16931_seller_vat_identifier': self._check_required_fields(
                vals['supplier'], 'vat'  # this check is larger than the rules above
            ),
            # [BR-61]-If the Payment means type code (BT-81) means SEPA credit transfer, Local credit transfer or
            # Non-SEPA international credit transfer, the Payment account identifier (BT-84) shall be present.
            # note: Payment account identifier is <cac:PayeeFinancialAccount>
            # note: no need to check account_number, because it's a required field for a partner_bank
            'cen_en16931_payment_account_identifier': self._check_required_fields(
                invoice, 'partner_bank_id'
            ) if vals['vals']['PaymentMeans_vals_list'][0]['payment_means_code'] in (30, 58) else None,
            # [BR-62]-The Seller electronic address (BT-34) shall have a Scheme identifier.
            # if this fails, it might just be a missing country when mapping the country to the EAS code
            'cen_en16931_seller_EAS': self._check_required_fields(
                vals['vals']['AccountingSupplierParty_vals']['Party_vals']['endpoint_id_attrs'], 'schemeID',
                _("No Electronic Address Scheme (EAS) could be found for %s.", vals['customer'].name)
            ),
            # [BR-63]-The Buyer electronic address (BT-49) shall have a Scheme identifier.
            # if this fails, it might just be a missing country when mapping the country to the EAS code
            'cen_en16931_buyer_EAS': self._check_required_fields(
                vals['vals']['AccountingCustomerParty_vals']['Party_vals']['endpoint_id_attrs'], 'schemeID',
                _("No Electronic Address Scheme (EAS) could be found for %s.", vals['customer'].name)
            ),
            # [BR-IC-12]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Deliver to country code (BT-80) shall not be blank.
            'cen_en16931_delivery_country_code': self._check_required_fields(
                vals['vals']['Delivery_vals_list'][0], 'Location_vals',
                _("For intracommunity supply, the delivery address should be included.")
            ) if intracom_delivery else None,

            # [BR-IC-11]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Actual delivery date (BT-72) or the Invoicing period (BG-14)
            # shall not be blank.
            'cen_en16931_delivery_date_invoicing_period': self._check_required_fields(
                vals['vals']['Delivery_vals_list'][0], 'actual_delivery_date',
                _("For intracommunity supply, the actual delivery date or the invoicing period should be included.")
            ) and self._check_required_fields(
                vals['vals']['InvoicePeriod_vals_list'][0], ['start_date', 'end_date'],
                _("For intracommunity supply, the actual delivery date or the invoicing period should be included.")
            ) if intracom_delivery else None,
        }

        for line in invoice.line_ids:
            if len(line.tax_ids) > 1:
                # [UBL-SR-48]-Invoice lines shall have one and only one classified tax category.
                constraints.update({'cen_en16931_tax_line': _("Each invoice line shall have one and only one tax.")})

        return constraints

    def _invoice_constraints_peppol_en16931_ubl(self, invoice, vals):
        """
        corresponds to the errors raised by 'schematron/openpeppol/3.13.0/xslt/PEPPOL-EN16931-UBL.xslt' for
        invoices in ecosio. This xslt was obtained by transforming the corresponding sch
        https://docs.peppol.eu/poacc/billing/3.0/files/PEPPOL-EN16931-UBL.sch.

        The national rules (https://docs.peppol.eu/poacc/billing/3.0/bis/#national_rules) are included in this file.
        They always refer to the supplier's country.
        """
        constraints = {
            # PEPPOL-EN16931-R020: Seller electronic address MUST be provided
            'peppol_en16931_ubl_seller_endpoint': self._check_required_fields(
                vals['supplier'], 'vat'
            ),
            # PEPPOL-EN16931-R010: Buyer electronic address MUST be provided
            'peppol_en16931_ubl_buyer_endpoint': self._check_required_fields(
                vals['customer'], 'vat'
            ),
            # PEPPOL-EN16931-R003: A buyer reference or purchase order reference MUST be provided.
            'peppol_en16931_ubl_buyer_ref_po_ref':
                "A buyer reference or purchase order reference must be provided." if self._check_required_fields(
                    vals['vals'], 'buyer_reference'
                ) and self._check_required_fields(invoice, 'invoice_origin') else None,
        }

        if vals['supplier'].country_id.code == 'NL':
            constraints.update({
                # [NL-R-001] For suppliers in the Netherlands, if the document is a creditnote, the document MUST contain
                # an invoice reference (cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID)
                'nl_r_001': self._check_required_fields(invoice, 'ref') if 'refund' in invoice.move_type else '',

                # [NL-R-002] For suppliers in the Netherlands the supplier’s address (cac:AccountingSupplierParty/cac:Party
                # /cac:PostalAddress) MUST contain street name (cbc:StreetName), city (cbc:CityName) and post code (cbc:PostalZone)
                'nl_r_002_street': self._check_required_fields(vals['supplier'], 'street'),
                'nl_r_002_zip': self._check_required_fields(vals['supplier'], 'zip'),
                'nl_r_002_city': self._check_required_fields(vals['supplier'], 'city'),

                # [NL-R-003] For suppliers in the Netherlands, the legal entity identifier MUST be either a
                # KVK or OIN number (schemeID 0106 or 0190)
                'nl_r_003': _(
                    "The supplier %s must have a KVK or OIN number.",
                    vals['supplier'].display_name
                ) if 'l10n_nl_oin' not in vals['supplier']._fields or 'l10n_nl_kvk' not in vals['supplier']._fields else '',

                # [NL-R-007] For suppliers in the Netherlands, the supplier MUST provide a means of payment
                # (cac:PaymentMeans) if the payment is from customer to supplier
                'nl_r_007': self._check_required_fields(invoice, 'partner_bank_id')
            })

            if vals['customer'].country_id.code == 'NL':
                constraints.update({
                    # [NL-R-004] For suppliers in the Netherlands, if the customer is in the Netherlands, the customer
                    # address (cac:AccountingCustomerParty/cac:Party/cac:PostalAddress) MUST contain the street name
                    # (cbc:StreetName), the city (cbc:CityName) and post code (cbc:PostalZone)
                    'nl_r_004_street': self._check_required_fields(vals['customer'], 'street'),
                    'nl_r_004_city': self._check_required_fields(vals['customer'], 'city'),
                    'nl_r_004_zip': self._check_required_fields(vals['customer'], 'zip'),

                    # [NL-R-005] For suppliers in the Netherlands, if the customer is in the Netherlands,
                    # the customer’s legal entity identifier MUST be either a KVK or OIN number (schemeID 0106 or 0190)
                    'nl_r_005': _(
                        "The customer %s must have a KVK or OIN number.",
                        vals['customer'].display_name
                    ) if 'l10n_nl_oin' not in vals['customer']._fields or 'l10n_nl_kvk' not in vals['customer']._fields else '',
                })

        if vals['supplier'].country_id.code == 'NO':
            vat = vals['supplier'].vat
            constraints.update({
                # NO-R-001: For Norwegian suppliers, a VAT number MUST be the country code prefix NO followed by a
                # valid Norwegian organization number (nine numbers) followed by the letters MVA.
                # Note: mva.is_valid("179728982MVA") is True while it lacks the NO prefix
                'no_r_001': _(
                    "The VAT number of the supplier does not seem to be valid. It should be of the form: NO179728982MVA."
                ) if not mva.is_valid(vat) or len(vat) != 14 or vat[:2] != 'NO' or vat[-3:] != 'MVA' else "",

                'no_supplier_bronnoysund': _(
                    "The supplier %s must have a Bronnoysund company registry.",
                    vals['supplier'].display_name
                ) if 'l10n_no_bronnoysund_number' not in vals['supplier']._fields or not vals['supplier'].l10n_no_bronnoysund_number else "",
            })
        if vals['customer'].country_id.code == 'NO':
            constraints.update({
                'no_customer_bronnoysund': _(
                    "The supplier %s must have a Bronnoysund company registry.",
                    vals['customer'].display_name
                ) if 'l10n_no_bronnoysund_number' not in vals['customer']._fields or not vals['customer'].l10n_no_bronnoysund_number else "",
            })

        return constraints
