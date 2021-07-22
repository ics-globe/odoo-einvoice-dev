# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DiscussChannel(models.Model):
    _name = 'discuss.channel'
    _description = "Discussion Channel"

    # common
    special_type = fields.Selection(string="Channel Type", selection=[('chat', "Chat"), ('channel', "Channel")], default='channel')

    # channel only
    channel_name = fields.Char(string="Name")
    channel_description = fields.Text(string="Description")
    channel_image_128 = fields.Image(string="Image", max_width=128, max_height=128)
    channel_members = fields.One2many(string='Members', comodel_name='discuss.channel.member', inverse_name='channel_id')
    channel_autosubscribe_group_ids = fields.Many2many(string="Auto Subscription", comodel_name='res.groups', relation='discuss_channel_autosubscribe_groups', help="Members of those groups will be automatically added as followers. Note that they will be able to manage their subscription manually if necessary.")
    channel_allowed_group_ids = fields.Many2many(string="Authorized Groups", comodel_name='res.groups', relation='discuss_channel_allowed_groups', help="The members of those groups will be able to find and join the channel.")

    # chat only
    chat_correspondent_low_id = fields.Many2one(string="First Correspondent", comodel_name='discuss.channel.member')
    chat_correspondent_high_id = fields.Many2one(string="Second Correspondent", comodel_name='discuss.channel.member')
