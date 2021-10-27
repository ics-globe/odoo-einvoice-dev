# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expense_alias_prefix = fields.Char('Default Alias Name for Expenses', compute='_compute_expense_alias_prefix',
        store=True, readonly=False)
    expense_use_mailgateway = fields.Boolean(string='Let your employees record expenses by email',
                                     config_parameter='hr_expense.use_mailgateway')

    module_hr_payroll_expense = fields.Boolean(string='Reimburse Expenses in Payslip')
    module_hr_expense_extract = fields.Boolean(string='Send bills to OCR to generate expenses')


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        expense_alias = self.env.ref('hr_expense.mail_alias_expense', raise_if_not_found=False)
        res.update(
            expense_alias_prefix=expense_alias.alias_name if expense_alias else False,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        expense_alias = self.env.ref('hr_expense.mail_alias_expense', raise_if_not_found=False)
        if not expense_alias and self.expense_alias_prefix:
            # create data again
            self.env['mail.alias'].sudo().create({
                'alias_contact': 'employees',
                'alias_model_id': self.env['ir.model']._get_id('hr.expense'),
                'alias_name': self.expense_alias_prefix,
            })
        elif expense_alias:
            expense_alias.write({'alias_name': self.expense_alias_prefix})

    @api.depends('expense_use_mailgateway')
    def _compute_expense_alias_prefix(self):
        self.filtered(lambda w: not w.expense_use_mailgateway).expense_alias_prefix = False
