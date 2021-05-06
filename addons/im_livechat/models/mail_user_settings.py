# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class MailUserSettings(models.Model):

    _inherit = 'mail.user.setttings'

    is_category_livechat_open = fields.Boolean("Is category livechat open", default=True)

    @api.model
    def _get_category_states_info(self, states):
        """ Override to add livechat category
        """
        info = super()._states_info(states)
        info['is_category_livechat_open'] = states.is_category_livechat_open
        return info

    @api.model
    def set_category_state(self, category, is_open):
        """ Override to add livechat category
        """
        states = self._get_states()
        if category == 'livechat':
            states.write({'is_category_livechat_open': is_open})
        return super().set_category_state(category, is_open)
