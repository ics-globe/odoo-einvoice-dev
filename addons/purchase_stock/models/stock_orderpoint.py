# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    @api.onchange('qty_multiple')
    def _onchange_qty_multiple(self):
        if not self.product_id or not self.qty_multiple or 'buy' not in self.rule_ids.mapped('action'):
            return
        purchase_packagings = self.product_id.packaging_ids.filtered('purchase')
        if purchase_packagings:
            packaging = purchase_packagings._find_suitable_product_packaging(self.qty_multiple, self.product_uom)
            if not packaging:
                msg = _("No packaging of quantity %d for this product. Available packagings: \n") % self.qty_multiple
                msg += "\n".join([" - %s: %d" % (p.name, p.qty) for p in purchase_packagings])
                return {'warning': {
                    'title': _("Warning"),
                    'message': msg,
                }}

    def _get_qty_multiple_to_order(self):
        """ Calculates the minimum quantity that can be ordered according to the
        qty of the product packaging.
        """
        if 'buy' in self.rule_ids.mapped('action'):
            purchase_packaging = self.product_id.packaging_ids.filtered('purchase')
            if purchase_packaging:
                return purchase_packaging[0].qty
        return super()._get_qty_multiple_to_order()
