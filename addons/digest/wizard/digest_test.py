# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class TestDigest(models.TransientModel):
    _name = 'digest.digest.test'
    _description = 'Sample Digest Wizard'

    email_to = fields.Text(string='Recipients', required=True,
        help='Carriage-return-separated list of email addresses.', default=lambda self: self.env.user.email_formatted)
    digest_id = fields.Many2one('digest.digest', string='Digest', required=True, ondelete='cascade')

    def send_mail_test(self):
        self.ensure_one()

        valid_emails = []
        for candidate in self.email_to.splitlines():
            parts = tools.email_split(candidate)
            if parts:
                valid_emails.append(parts[0])

        users = self.env['res.users'].search([
            ('partner_id.email_normalized', 'in', valid_emails)
        ])

        for user in users:
            self.digest_id._action_send_to_user(user, consum_tips=False, force_send=True)
