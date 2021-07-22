# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DiscussChannelMember(models.Model):
    _name = 'discuss.channel.member'
    _description = "Discussion Channel Member"

    # definition
    channel_id = fields.Many2one(string="Channel", comodel_name='discuss.channel', required=True)
    member_id = fields.Many2one(string="Member", comodel_name='res.identity', required=True)

    # state
    desktop_popout_state = fields.Selection(string="Popout State", selection=[('opened', "Opened"), ('folded', "Folded"), ('closed', "Closed")], default='opened')
    last_fetched_message_id = fields.Many2one(string="Last Fetched Message", comodel_name='discuss.channel.message')
    last_seen_message_id = fields.Many2one(string="Last Seen Message", comodel_name='discuss.channel.message')

    # chat only
    chat_is_pinned = fields.Boolean(string="Is chat visible on the interface?", default=True)
    chat_custom_name = fields.Char(string="Custom Chat Name")
