import re

from odoo import fields, api, models

from odoo.addons.base_vat.models.res_partner import _ref_vat

_ref_vat['ph'] = '123-456-789-01234'

class ResPartner(models.Model):
    _inherit = "res.partner"

    branch_code = fields.Char("Branch Code", default='000', required=True)
    first_name = fields.Char("First Name")
    middle_name = fields.Char("Middle Name")
    last_name = fields.Char("Last Name")

    @api.model
    def _commercial_fields(self):
        fields = super()._commercial_fields()
        fields.append('branch_code')
        return fields

    __check_vat_ph_re = re.compile(r"\d{3}-\d{3}-\d{3}-\d{5}")

    def check_vat_ph(self, vat):
        return len(vat) == 17 and self.__check_vat_ph_re.match(vat)
