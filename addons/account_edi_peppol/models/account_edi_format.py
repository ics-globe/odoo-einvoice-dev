# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo import _, models, fields
from odoo.exceptions import UserError
from odoo.tests.common import Form

# Electronic Address Scheme (EAS), see https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/
COUNTRY_EAS = {
    'HU': 9910,

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


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _is_edi_peppol_customer_valid(self, customer):
        return customer.country_id.code in COUNTRY_EAS

    def _get_edi_peppol_builder(self, company_country_code):
        self.ensure_one()
        if self.code != 'peppol':
            return

        if company_country_code == 'DE':
            # XRechnung (DE)
            return {
                'invoice_xml_builder': self.env['account.edi.xml.ubl_de'],
                'invoice_filename': lambda inv: 'factur-x.xml',
                'invoice_embed_to_pdf': True,
            }
        if company_country_code == 'FR':
            # Factur-x (FR)
            return {
                'invoice_xml_builder': self.env['account.edi.xml.ubl_bis3'],
                'invoice_filename': lambda inv: 'factur-x.xml',
                'invoice_embed_to_pdf': True,
            }
        if company_country_code in COUNTRY_EAS:
            return {
                'invoice_xml_builder': self.env['account.edi.xml.ubl_bis3'],
                'invoice_filename': lambda inv: f"{inv.name.replace('/', '_')}_peppol.xml",
            }

    def _get_edi_peppol_info(self, company, customer=None):
        self.ensure_one()

        if not company.country_id:
            return
        if customer is not None and not self._is_edi_peppol_customer_valid(customer):
            return

        return self._get_edi_peppol_builder(company.country_id.code.upper())

    ####################################################
    # Import: Account.edi.format override
    ####################################################

    def _create_invoice_from_xml_tree(self, journal, filename, tree):
        # OVERRIDE
        self.ensure_one()

        peppol_info = self._get_edi_peppol_info(journal.company_id)
        if peppol_info:
            invoice = peppol_info['invoice_xml_builder']._import_invoice(journal, filename, tree)
            if invoice:
                return invoice

        return super()._create_invoice_from_xml_tree(journal, filename, tree)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        # OVERRIDE
        self.ensure_one()

        peppol_info = self._get_edi_peppol_info(invoice.journal_id.company_id)
        if peppol_info:
            invoice = peppol_info['invoice_xml_builder']._import_invoice(invoice.journal_id, filename, tree, existing_invoice=invoice)
            if invoice:
                return invoice

        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    ####################################################
    # Export: Account.edi.format override
    ####################################################

    def _is_required_for_invoice(self, invoice):
        # OVERRIDE
        self.ensure_one()

        if self.code == 'peppol':
            if invoice.move_type not in ('out_invoice', 'out_refund'):
                return False

            peppol_info = self._get_edi_peppol_info(invoice.company_id, customer=invoice.partner_id)
            return bool(peppol_info)

        return super()._is_required_for_invoice(invoice)

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        self.ensure_one()

        peppol_info = self._get_edi_peppol_info(journal.company_id)
        if peppol_info:
            return True

        return super()._is_compatible_with_journal(journal)

    def _is_enabled_by_default_on_journal(self, journal):
        # OVERRIDE
        self.ensure_one()

        peppol_info = self._get_edi_peppol_info(journal.company_id)
        if peppol_info:
            return True

        return super()._is_enabled_by_default_on_journal(journal)

    def _post_invoice_edi(self, invoices, test_mode=False):
        # OVERRIDE
        self.ensure_one()

        if self.code != 'peppol':
            return super()._post_invoice_edi(invoices)

        peppol_info = self._get_edi_peppol_info(invoices.company_id, customer=invoices.partner_id)

        res = {}
        for invoice in invoices:
            xml_content, errors = peppol_info['invoice_xml_builder']._export_invoice(invoice)
            if errors:
                res[invoice] = {'error': '\n'.join(set(errors))}
            else:
                attachment = self.env['ir.attachment'].create({
                    'name': peppol_info['invoice_filename'](invoice),
                    'raw': xml_content.encode(),
                    'res_model': 'account.move',
                    'res_id': invoice.id,
                    'mimetype': 'application/xml'
                })
                res[invoice] = {'success': True, 'attachment': attachment}

        return res

    def _is_embedding_to_invoice_pdf_needed(self, invoice):
        # OVERRIDE
        self.ensure_one()

        peppol_info = self._get_edi_peppol_info(invoice.company_id, customer=invoice.partner_id)
        if peppol_info:
            return peppol_info.get('invoice_embed_to_pdf', False)

        return super()._is_embedding_to_invoice_pdf_needed(invoice)
