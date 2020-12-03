# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    l10n_in_journal_id = fields.Many2one('account.journal', string='Journal', \
        states=Purchase.READONLY_STATES, domain="[('type', '=', 'purchase')]")

    l10n_in_gst_treatment = fields.Selection([
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export')
        ], string='GST Treatment', states=Purchase.READONLY_STATES)

    l10n_in_company_country_code = fields.Char(related='company_id.country_id.code', 
        string='Country code')

    l10n_in_company_partner_id = fields.Many2one(compute='compute_l10n_in_company_partner_id',
        comodel_name='res.partner',
        string='Company/GSTN Unit')

    def compute_l10n_in_company_partner_id(self):
        for order in self:
            order.l10n_in_company_partner_id = order.l10n_in_journal_id and order.l10n_in_journal_id.l10n_in_gstin_partner_id or \
                order.company_id.partner_id

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.l10n_in_company_country_code == 'IN':
            invoice_vals['l10n_in_gst_treatment'] = self.l10n_in_gst_treatment
            invoice_vals['l10n_in_gstin'] = self.partner_id.vat
            invoice_vals['l10n_in_state_id'] = self.l10n_in_company_partner_id.state_id.id
            invoice_vals['partner_shipping_id'] = self.partner_id.id
        return invoice_vals

    @api.onchange('company_id')
    def l10n_in_onchange_company_id(self):
        if self.l10n_in_company_country_code == 'IN':
            domain = [('company_id', '=', self.company_id.id), ('type', '=', 'purchase')]
            journal = self.env['account.journal'].search(domain, limit=1)
            if journal:
                self.l10n_in_journal_id = journal.id

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        if self.l10n_in_company_country_code == 'IN':
            self.l10n_in_gst_treatment = self.partner_id.l10n_in_gst_treatment
        return super().onchange_partner_id()
