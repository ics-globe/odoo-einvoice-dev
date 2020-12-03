# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    def compute_l10n_in_shipping_partner(self):
        for invoice in self:
            invoice.l10n_in_shipping_partner_id = invoice.partner_shipping_id or invoice.partner_id

    @api.onchange('partner_shipping_id', 'partner_id', 'company_id')
    def onchange_partner_shipping_id(self):
        if self.l10n_in_company_country_code == 'IN':
            if self.journal_id.type == 'sale':
                self.l10n_in_state_id = self.l10n_in_partner_state_id.id
            elif self.journal_id.type == 'purchase':
                self.l10n_in_state_id = self.l10n_in_company_partner_id.state_id.id
        