# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DeliveryZipPrefix(models.Model):
    """ Zip prefix that a delivery.carrier will deliver to. """
    _name = 'delivery.zip.prefix'
    _description = 'Delivery Zip Prefix'

    name = fields.Char('Prefix', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Prefix already exists!"),
    ]
