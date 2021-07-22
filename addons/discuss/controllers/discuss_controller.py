# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class DiscussController(http.Controller):

    @http.route('/discuss/init_messaging', type='json', auth='user')
    def discuss_init_messaging(self):
        values = {
            # 'needaction_inbox_counter': request.env['res.partner'].get_needaction_count(),
            # 'starred_counter': request.env['res.partner'].get_starred_count(),
            # 'channel_slots': request.env['mail.channel'].channel_fetch_slot(),
            # 'mail_failures': request.env['mail.message'].message_fetch_failed(),
            'commands': request.env['mail.channel'].get_mention_commands(),
            'shortcodes': request.env['mail.shortcode'].sudo().search_read([], ['source', 'substitution', 'description']),
            'menu_id': request.env['ir.model.data'].xmlid_to_res_id('mail.menu_root_discuss'),
            'partner_root': request.env.ref('base.partner_root').sudo().mail_partner_format(),
            'public_partners': [partner.mail_partner_format() for partner in request.env.ref('base.group_public').sudo().with_context(active_test=False).users.partner_id],
            'current_partner': request.env.user.partner_id.mail_partner_format(),
            'current_user_id': request.env.user.id,
        }
        return values
