# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_stock_delivery_count = fields.Boolean('#Delivery')
    kpi_stock_delivery_count_value = fields.Integer(compute='_compute_kpi_stock_delivery_count_value')
    kpi_stock_receipt_count = fields.Boolean('#Receipt')
    kpi_stock_receipt_count_value = fields.Integer(compute='_compute_kpi_stock_receipt_count_value')

    def _compute_picking_count_gen(self, picking_type_code):
        """ Compute the number of picking of the given type for each record kpi parameters
        and yield the record and the computed value.
        """
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            yield record, self.env['stock.picking'].search_count(
                [('picking_type_id.code', '=', picking_type_code),
                 ('state', '=', 'done'),
                 ('date_done', '>=', start),
                 ('date_done', '<', end),
                 ('company_id', '=', company.id)])

    def _compute_kpi_stock_delivery_count_value(self):
        for record, value in self._compute_picking_count_gen('outgoing'):
            record.kpi_stock_delivery_count_value = value

    def _compute_kpi_stock_receipt_count_value(self):
        for record, value in self._compute_picking_count_gen('incoming'):
            record.kpi_stock_receipt_count_value = value
