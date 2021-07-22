# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DiscussMessage(models.Model):
    _name = 'discuss.channel.message'
    _description = "Discussion Message"

    # common
    channel_id = fields.Many2one(string="Channel", comodel_name='discuss.channel', required=True)
    author_id = fields.Many2one(string="Author", comodel_name='res.identity', required=True)
    message_type = fields.Selection(string="Message Type", selection=[('message', "User Message"), ('join', "Join"), ('leave', "Leave")], default='message')
    attachment_ids = fields.Many2many(string="Attachments", comodel_name='ir.attachment', column1='message_id', column2='attachment_id')
    mentioned_person_ids = fields.Many2many(string="Mentioned persons", comodel_name='res.identity')

    # message only
    message_content = fields.Html(string="Content", sanitize_style=True)
    message_in_reply_to_message_id = fields.Many2one(string="In reply to message", comodel_name='discuss.channel.message')
