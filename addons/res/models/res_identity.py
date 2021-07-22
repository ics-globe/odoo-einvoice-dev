# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResIdentity(models.Model):
    _name = 'res.identity'
    _inherit = ['image.mixin']
    _description = "Identity"

    name = fields.Char(string="Name")
