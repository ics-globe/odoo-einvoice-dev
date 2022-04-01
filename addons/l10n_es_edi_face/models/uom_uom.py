# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class UoM(models.Model):
    _inherit = 'uom.uom'
    l10n_es_edi_face_uom_code = fields.Selection(
            [
                ('01', _('Units')),
                ('02', _('Hours')),
                ('03', _('Kilograms')),
                ('04', _('Liters')),
                ('05', _('Other')),
                ('06', _('Boxes')),
                ('07', _('Trays, one layer no cover, plastic')),
                ('08', _('Barrels')),
                ('09', _('Jerricans, cylindrical')),
                ('10', _('Bags')),
                ('11', _('Carboys, non-protected')),
                ('12', _('Bottles, non-protected, cylindrical')),
                ('13', _('Canisters')),
                ('14', _('Tetra Briks')),
                ('15', _('Centiliters')),
                ('16', _('Centimeters')),
                ('17', _('Bins')),
                ('18', _('Dozens')),
                ('19', _('Cases')),
                ('20', _('Demijohns, non-protected')),
                ('21', _('Grams')),
                ('22', _('Kilometers')),
                ('23', _('Cans, rectangular')),
                ('24', _('Bunches')),
                ('25', _('Meters')),
                ('26', _('Milimeters')),
                ('27', _('6-Packs')),
                ('28', _('Packages')),
                ('29', _('Portions')),
                ('30', _('Rolls')),
                ('31', _('Envelopes')),
                ('32', _('Tubs')),
                ('33', _('Cubic meter')),
                ('34', _('Second')),
                ('35', _('Watt')),
                ('36', _('KiloWatt Hour')),
            ],
            string='Spanish EDI Units', default="05", required=True)
