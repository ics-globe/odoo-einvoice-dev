# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUBL21(models.AbstractModel):
    _name = "account.edi.xml.ubl_21"
    _inherit = 'account.edi.xml.ubl_20'
    _description = "UBL 2.1"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    # OVERRIDE account.edi.xml.ubl_20
    def _get_xml_builder(self, format_code, company):
        if format_code == 'ubl_2_1':
            return {
                'export_invoice': self._export_invoice,
                'invoice_filename': lambda inv: f"{inv.name.replace('/', '_')}_ubl_21.xml",
                'ecosio_format': {
                    'invoice': 'org.oasis-open:invoice:2.1',
                    'credit_note': 'org.oasis-open:creditnote:2.1',
                },
            }

    # EXTENDS account.edi.xml.ubl_20
    def _export_invoice_vals(self, invoice):
        vals = super()._export_invoice_vals(invoice)

        vals.update({
            'InvoiceType_template': 'account_edi_ubl_cii.ubl_21_InvoiceType',
            'InvoiceLineType_template': 'account_edi_ubl_cii.ubl_21_InvoiceLineType',
        })

        vals['vals'].update({
            'ubl_version_id': 2.1,
            'buyer_reference': vals['customer'].commercial_partner_id.name,
        })

        return vals
