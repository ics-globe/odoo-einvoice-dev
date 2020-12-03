# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import fields, models, tools


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', check_company=True,
        domain="[('type', '=', 'opportunity'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    def action_confirm(self):
        return super(SaleOrder, self.with_context(
            tools.clean_context(self.env.context, exclude=re.compile(r'default_tag_ids$').match)
        )).action_confirm()
