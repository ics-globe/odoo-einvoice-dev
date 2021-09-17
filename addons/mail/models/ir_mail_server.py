# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    def _get_default_bounce_address(self):
        bounce_alias = self._alias_get_bounce_alias()
        catchall_domain = self._alias_get_domain()
        if catchall_domain:
            return '%s@%s' % (bounce_alias or 'postmaster-odoo', catchall_domain)

    def _get_default_from_address(self):
        catchall_domain = self._alias_get_domain()
        email_from = self.env['ir.config_parameter'].sudo().get_param("mail.default.from")
        if email_from and catchall_domain:
            return "%s@%s" % (email_from, catchall_domain)
        return super(IrMailServer, self)._get_default_from_address()
