# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class Website(models.Model):
    _inherit = 'website'

    google_places_api_key = fields.Char('Google Places API Key')
