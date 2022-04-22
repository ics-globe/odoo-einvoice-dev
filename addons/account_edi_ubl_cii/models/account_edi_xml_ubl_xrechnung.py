# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUBLDE(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = 'account.edi.xml.ubl_de'
    _description = "BIS3 DE (XRechnung)"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _get_xml_builder(self, format_code, company):
        if format_code == 'ubl_de' and company.country_id.code == 'DE':
            return {
                'export_invoice': self._export_invoice,
                'invoice_filename': lambda inv: f"{inv.name.replace('/', '_')}_ubl_de.xml",
                'ecosio_format': {
                    'invoice': 'de.xrechnung:ubl-invoice:2.2.0',
                    'credit_note': 'de.xrechnung:ubl-creditnote:2.2.0',
                },
            }

    def _export_invoice_vals(self, invoice):
        # OVERRIDE
        vals = super()._export_invoice_vals(invoice)

        vals['vals'].update({
            'customization_id': 'urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_2.2#conformant#urn:xoev-de:kosit:extension:xrechnung_2.2',
            'buyer_reference': invoice.commercial_partner_id.name,
        })

        return vals

    def _export_invoice_constraints(self, invoice, vals):
        # OVERRIDE
        constraints = super()._export_invoice_constraints(invoice, vals)

        constraints.update({
            'bis3_de_supplier_telephone_required': self._check_required_fields(vals['supplier'], ['phone', 'mobile']),
            'bis3_de_supplier_electronic_mail_required': self._check_required_fields(vals['supplier'], 'email'),
        })

        return constraints
