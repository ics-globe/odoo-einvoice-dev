# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUBLNO(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = 'account.edi.xml.ubl_no'
    _description = "EHF Billing/Fakturering 3.0"

    """
    * Documentation of EHF Billing 3.0: https://anskaffelser.dev/postaward/g3/
    * EHF 2.0 is no longer used:
      https://anskaffelser.dev/postaward/g2/announcement/2019-11-14-removal-old-invoicing-specifications/
    * Official doc for EHF Billing 3.0 is the OpenPeppol BIS 3 doc +
      https://anskaffelser.dev/postaward/g3/spec/current/billing-3.0/norway/

        "Based on work done in PEPPOL BIS Billing 3.0, Difi has included Norwegian rules in PEPPOL BIS Billing 3.0 and
        does not see a need to implement a different CIUS targeting the Norwegian market. Implementation of EHF Billing
        3.0 is therefore done by implementing PEPPOL BIS Billing 3.0 without extensions or extra rules."

    Thus, EHF 3 and Bis 3 are actually the same format. The specific rules for NO defined in Bis 3 are added in Bis 3.
    """

    def _get_xml_builder(self, format_code, company):
        # the EDI option will only appear on the journal of norvegian companies
        if format_code == 'ehf_3' and company.country_id.code == 'NO':
            return {
                'export_invoice': self._export_invoice,
                'invoice_filename': lambda inv: f"{inv.name.replace('/', '_')}_ehf3.xml",
                'ecosio_format': {
                    'invoice': 'eu.peppol.bis3:invoice:3.13.0',
                    'credit_note': 'eu.peppol.bis3:creditnote:3.13.0',
                },
            }
