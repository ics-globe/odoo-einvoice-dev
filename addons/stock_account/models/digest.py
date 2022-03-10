# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_stock_valuation_total = fields.Boolean('Total Inventory Valuation')
    kpi_stock_valuation_total_value = fields.Monetary(compute='_compute_kpi_stock_valuation_total_value')

    def _compute_kpi_stock_valuation_total_value(self):
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            results = self.env['stock.valuation.layer'] \
                .read_group([('company_id', '=', company.id),
                             ('create_date', '>=', start),
                             ('create_date', '<', end)],
                            ['value:sum'],
                            [])
            self.kpi_stock_valuation_total_value = results[0]['value'] if results else 0
