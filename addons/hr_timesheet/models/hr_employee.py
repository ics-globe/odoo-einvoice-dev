# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    timesheet_cost = fields.Monetary('Cost', currency_field='currency_id',
    	groups="hr.group_hr_user", default=0.0)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    def name_get(self):
        res = super().name_get()
        name = dict(res)
        for employee in self:
            if len(employee.user_id.company_ids) > 1 and len(self.env.context.get('allowed_company_ids', [])) > 1:
                name[employee.id] = f'{name[employee.id]} ({employee.company_id.name})'
        return list(name.items())
