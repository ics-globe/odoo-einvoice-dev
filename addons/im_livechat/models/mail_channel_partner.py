# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ChannelPartner(models.Model):
    _inherit = 'mail.channel.partner'

    @api.autovacuum
    def _gc_unpin_livechat_sessions(self):
        """ Unpin livechat sessions with no activity for at least one day to
            clean the operator's interface """
        self.env.cr.execute("""
            SELECT cp.id FROM mail_channel_partner cp
            INNER JOIN mail_channel c on c.id = cp.channel_id
            WHERE c.channel_type = 'livechat' AND cp.is_pinned is true AND
                cp.last_seen_dt < current_timestamp - interval '1 day'
        """)
        cp_records = self.env['mail.channel.partner'].browse([id[0] for id in self.env.cr.fetchall()])
        sessions_to_be_unpinned = cp_records.filtered(lambda cp: cp.message_unread_counter == 0)
        if(len(sessions_to_be_unpinned) > 0):
            self.env.cr.execute("""
                UPDATE mail_channel_partner
                SET is_pinned = false
                WHERE id in %s""", (tuple(sessions_to_be_unpinned.mapped('id')),))
