# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # ==== Business fields ====
    cpf_code = fields.Char(string="CPF", help="Natural Persons Register.")
    ie_code = fields.Char(string="IE", help="State Tax Identification Number. Should contain 9-14 digits.") # each state has its own format. Not all of the validation rules can be easily found.
    im_code = fields.Char(string="IM", help="Municipal Tax Identification Number") # each municipality has its own format. There is no information about validation anywhere.
    nire_code = fields.Char(string="NIRE", help="State Commercial Identification Number. Should contain 11 digits.")
