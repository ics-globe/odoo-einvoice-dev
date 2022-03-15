# -*- coding: utf-8 -*-
from odoo import models, _


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _name = "account.edi.xml.ubl_bis3"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL BIS Billing 3.0"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _get_country_vals(self, country):
        # OVERRIDE
        vals = super()._get_country_vals(country)

        vals.pop('name', None)

        return vals

    def _get_partner_party_tax_scheme_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_party_tax_scheme_vals(partner)

        vals.pop('registration_name', None)
        vals.pop('RegistrationAddress_vals', None)

        return vals

    def _get_partner_party_legal_entity_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_party_legal_entity_vals(partner)

        vals.pop('RegistrationAddress_vals', None)

        return vals

    def _get_partner_contact_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_contact_vals(partner)

        vals.pop('id', None)

        return vals

    def _get_partner_party_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_party_vals(partner)

        vals['endpoint_id'] = partner.vat
        vals['endpoint_id_attrs'] = {'schemeID': self._get_eas_mapping().get(partner.country_id.code)}

        return vals

    def _get_delivery_vals(self, invoice):
        # OVERRIDE
        supplier = invoice.company_id.partner_id.commercial_partner_id
        customer = invoice.commercial_partner_id
        intracom_delivery = (customer.country_id in self.env.ref('base.europe').country_ids
                             and supplier.country_id in self.env.ref('base.europe').country_ids
                             and supplier.country_id != customer.country_id)

        delivery_date = None
        if 'partner_shipping_id' in invoice._fields:
            partner_shipping_id = invoice.partner_shipping_id
        elif intracom_delivery:
            # need a default in this case
            # [BR-IC-12]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Deliver to country code (BT-80) shall not be blank.
            partner_shipping_id = customer
            # need a default also for the delivery_date
            # [BR-IC-11]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Actual delivery date (BT-72) or the Invoicing period (BG-14)
            # shall not be blank.
            delivery_date = invoice.invoice_date
        else:
            return

        return {
            'actual_delivery_date': delivery_date,
            'delivery_location': {
                'DeliveryAddress_vals': self._get_partner_address_vals(partner_shipping_id),
            },
        }

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
            vals.pop('name', None)

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

        vals['PartyType_template'] = 'account_edi_ubl_cii.ubl_bis3_PartyType'

        vals['vals'].update({
            'customization_id': 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0',
            'profile_id': 'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0',
            'currency_dp': 2,
        })
        vals['vals']['LegalMonetaryTotal_vals']['currency_dp'] = 2

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
        corresponds to the errors raised by ' schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt' for invoices
        """
        intracom_delivery = (vals['customer'].country_id in self.env.ref('base.europe').country_ids
                             and vals['supplier'].country_id in self.env.ref('base.europe').country_ids
                             and vals['customer'].country_id != vals['supplier'].country_id)
        return {
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
            ) if vals['vals']['PaymentMeans_vals'][0]['payment_means_code'] in (30, 58) else None,
            # [BR-63]-The Buyer electronic address (BT-49) shall have a Scheme identifier.
            # if this fails, it might just be a missing country when mapping the country to the EAS code
            'cen_en16931_buyer_EAS': self._check_required_fields(
                vals['vals']['AccountingCustomerParty_vals']['Party_vals']['endpoint_id_attrs'], 'schemeID',
                _("No Electronic Address Scheme (EAS) could be found for %s.", vals['customer'].name)
            ),
            # [BR-IC-12]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Deliver to country code (BT-80) shall not be blank.
            'cen_en16931_delivery_country_code': self._check_required_fields(
                vals['vals']['Delivery_vals'], 'delivery_location',
                _("For intracommunity supply, the delivery address should be included.")
            ) if intracom_delivery else None,

            # [BR-IC-11]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Actual delivery date (BT-72) or the Invoicing period (BG-14)
            # shall not be blank.
            'cen_en16931_delivery_date_invoicing_period': self._check_required_fields(
                vals['vals']['Delivery_vals'], 'actual_delivery_date',
                _("For intracommunity supply, the actual delivery date or the invoicing period should be included.")
            ) and self._check_required_fields(
                vals['vals']['InvoicePeriod_vals'], ['start_date', 'end_date'],
                _("For intracommunity supply, the actual delivery date or the invoicing period should be included.")
            ) if intracom_delivery else None,
        }

    def _invoice_constraints_peppol_en16931_ubl(self, invoice, vals):
        """
        corresponds to the errors raised by 'schematron/openpeppol/3.13.0/xslt/PEPPOL-EN16931-UBL.xslt' for
        invoices
        """
        return {
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
