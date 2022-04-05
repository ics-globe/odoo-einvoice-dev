# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUBL21(models.AbstractModel):
    _name = "account.edi.xml.ubl_21"
    _inherit = 'account.edi.xml.ubl_20'
    _description = "UBL 2.1"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _get_invoice_payment_means_vals_list(self, invoice):
        # OVERRIDE
        vals_list = super()._get_invoice_payment_means_vals_list(invoice)
        for vals in vals_list:
            # SEPA Direct Debit (example: https://anskaffelser.dev/postaward/g3/spec/current/billing-3.0/norway/#_sepa_direct_debit)
            # PaymentMandate is ready to be used
            vals.update({
                'PaymentMandate_vals': {
                    'mandate_ref_id': None,
                    'account_iban': None,
                }
            })
        return vals_list

    def _export_invoice_vals(self, invoice):
        # OVERRIDE
        vals = super()._export_invoice_vals(invoice)

        vals.update({
            'InvoiceType_template': 'account_edi_ubl_cii.ubl_21_InvoiceType',
            'InvoiceLineType_template': 'account_edi_ubl_cii.ubl_21_InvoiceLineType',
            'PaymentMeansType_template': 'account_edi_ubl_cii.ubl_21_PaymentMeansType',
            'PaymentMandateType_template': 'account_edi_ubl_cii.ubl_21_PaymentMandateType',
        })

        vals['vals'].update({
            'ubl_version_id': 2.1,
            'buyer_reference': vals['customer'].commercial_partner_id.name,
        })

        return vals
