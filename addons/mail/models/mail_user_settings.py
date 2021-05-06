# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailUserSettings(models.Model):
    _name = 'mail.user.settings'
    _description = 'User Settings'

    is_category_channel_open = fields.Boolean(string='Is category channel open', default=True)
    is_category_chat_open = fields.Boolean(string='Is category chat open', default=True)
    user_id = fields.Many2one('res.users', string='User', required=True)

    @api.model
    def _get_settings(self):
        user_id = self.env.user.id
        settings = self.env['mail.user.settings'].search([
            ('user_id', '=', user_id),
        ], limit=1)
        if not settings:
            settings = self.create({'user_id': user_id})
        return settings

    @api.model
    def _get_category_states_info(self, settings):
        return {
            "is_category_channel_open": settings.is_category_channel_open,
            "is_category_chat_open": settings.is_category_chat_open,
        }

    @api.model
    def get_category_states(self):
        settings = self._get_settings()
        return self._get_category_states_info(settings)

    @api.model
    def set_category_state(self, category, is_open):
        settings = self._get_settings()
        if category == 'chat':
            settings.write({'is_category_chat_open': is_open})
        elif category == 'channel':
            settings.write({'is_category_channel_open': is_open})
        notif = self._get_category_states_info(settings)
        notif['type'] = 'category_states'
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', settings.user_id.partner_id.id), notif)
