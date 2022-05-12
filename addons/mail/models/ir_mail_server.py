# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class IrMailServer(models.Model):
    _name = 'ir.mail_server'
    _inherit = ['ir.mail_server']

    mail_template_ids = fields.One2many(
        comodel_name='mail.template',
        inverse_name='mail_server_id',
        string='Mail template using this mail server',
        readonly=True)

    def _active_usages_compute(self):
        usages = super(IrMailServer, self)._active_usages_compute()
        usages.extend(map(lambda t: _('%s (Email Template)', t.display_name), self.mail_template_ids))
        return usages
