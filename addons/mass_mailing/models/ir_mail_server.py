# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class IrMailServer(models.Model):
    _name = 'ir.mail_server'
    _inherit = ['ir.mail_server']

    active_mailing_ids = fields.One2many(
        comodel_name='mailing.mailing',
        inverse_name='mail_server_id',
        string='Active mailing using this mail server',
        readonly=True,
        domain=[('state', '!=', 'done'), ('active', '=', True)])

    def _active_usages_compute(self):
        usages = super(IrMailServer, self)._active_usages_compute()
        if self.env['mailing.mailing']._get_default_mail_server_id() == self.id:
            usages.append(_('Email Marketing uses it as default mail server to send mailing'))
        usages.extend(map(lambda m: _('%s (Mailing)', m.display_name), self.active_mailing_ids))
        return usages
