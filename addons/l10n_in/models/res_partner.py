# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_in_gst_treatment = fields.Selection([
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export'),
        ], string="GST Treatment")
    
    def _get_l10n_in_gst_treatment(self):
        self.ensure_one()
        
        l10n_in_gst_treatment = 'regular'
        if self.country_id and self.country_id.code != 'IN':
            l10n_in_gst_treatment = 'overseas'
        elif self.country_id and self.country_id.code == 'IN':
            l10n_in_gst_treatment = (self.company_type == 'company') and 'regular' or 'consumer'
        return l10n_in_gst_treatment

    @api.onchange('company_type')
    def onchange_company_type(self):
        res = super().onchange_company_type()
        self.l10n_in_gst_treatment = self._get_l10n_in_gst_treatment()
        return res

    @api.onchange('country_id')
    def _onchange_country_id(self):
        res = super()._onchange_country_id()
        self.l10n_in_gst_treatment = self._get_l10n_in_gst_treatment()
        return res

    @api.model
    def _commercial_fields(self):
        res = super()._commercial_fields()
        return res + ['l10n_in_gst_treatment']
