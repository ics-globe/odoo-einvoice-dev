# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class HrExpenseSplit(models.TransientModel):

    _name = 'hr.expense.split'
    _description = 'Expense Split'

    def default_get(self, fields):
        result = super(HrExpenseSplit, self).default_get(fields)
        if 'expense_id' in result:
            expense = self.env['hr.expense'].browse(result['expense_id'])
            result['total_amount'] = 0.0
            result['name'] = expense.name
            result['tax_ids'] = expense.tax_ids
            result['product_id'] = expense.product_id
            result['company_id'] = expense.company_id
            result['analytic_account_id'] = expense.analytic_account_id
            result['employee_id'] = expense.employee_id
            result['currency_id'] = expense.currency_id
        return result

    name = fields.Char('Description', required=True)
    wizard_id = fields.Many2one('hr.expense.split.wizard')
    expense_id = fields.Many2one('hr.expense', string='Expense')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    tax_ids = fields.Many2many('account.tax', domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase'), ('price_include', '=', True)]")
    total_amount = fields.Monetary("Total In Currency", required=True)
    amount_tax = fields.Monetary(string='Tax amount in Currency', compute='_compute_amount_tax')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', check_company=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    company_id = fields.Many2one('res.company')
    currency_id = fields.Many2one('res.currency')
    product_has_tax = fields.Boolean("Whether tax is defined on a selected product", compute='_compute_product_has_tax')

    @api.depends('total_amount', 'tax_ids')
    def _compute_amount_tax(self):
        for split in self:
            taxes = split.tax_ids.compute_all(price_unit=split.total_amount, currency=split.currency_id, quantity=1, product=split.product_id)
            split.amount_tax = taxes['total_included'] - taxes['total_excluded']

    @api.onchange('product_id')
    def _onchage_product_id(self):
        self.tax_ids = self.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == self.company_id)

    @api.depends('product_id')
    def _compute_product_has_tax(self):
        for split in self:
            split.product_has_tax = split.product_id and split.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == split.company_id)
