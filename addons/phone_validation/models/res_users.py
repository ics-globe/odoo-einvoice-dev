# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.addons.phone_validation.tools import phone_validation


class Users(models.Model):
    _inherit = 'res.users'

    @api.model
    def _deactivate_portal_user(self, **post):
        """Blacklist the phone of the user after deleting it."""
        numbers_to_blacklist = []
        if post.get('blacklist'):
            for user in self:
                sanitized = phone_validation.phone_sanitize_numbers_w_record([user.phone, user.mobile], user)
                user_phone = sanitized[user.phone]['sanitized']
                user_mobile = sanitized[user.mobile]['sanitized']
                if user_phone:
                    numbers_to_blacklist.append(user_phone)
                if user_mobile:
                    numbers_to_blacklist.append(user_mobile)

        super(Users, self)._deactivate_portal_user(**post)

        if numbers_to_blacklist:
            blacklists = self.env['phone.blacklist']._add(numbers_to_blacklist)
            for blacklist in blacklists:
                blacklist._message_log(body=_('The phone has been blacklisted because its related portal user has deactivated his account.'))
