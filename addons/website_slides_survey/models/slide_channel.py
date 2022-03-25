# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Channel(models.Model):
    _inherit = 'slide.channel'

    nbr_certification = fields.Integer("Number of Certifications", compute='_compute_slides_statistics', store=True)

    def _remove_membership(self, partner_ids):
        res = super()._remove_membership(partner_ids)
        user_inputs = self.env['survey.user_input'].sudo().search([
            ('survey_id', 'in', self.slide_ids.survey_id.ids),
            ('partner_id', 'in', partner_ids),
        ])
        user_inputs.action_archive()
        return res

    def _action_add_members(self, target_partners, **member_values):
        res = super()._action_add_members(target_partners, **member_values)
        user_inputs = self.env['survey.user_input'].with_context(active_test=False).sudo().search([
            ('survey_id', 'in', self.slide_ids.survey_id.ids),
            ('partner_id', 'in', target_partners.ids),
            ('active', '=', False)
        ])
        if user_inputs:
            user_inputs.action_unarchive()
        return res
