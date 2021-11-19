# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MassMailingContact(models.Model):
    _inherit = 'mailing.contact'

    @api.model
    def _get_searchable_fields(self):
        return ['email']
