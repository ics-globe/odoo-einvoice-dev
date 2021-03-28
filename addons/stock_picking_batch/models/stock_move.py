from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    batch_picking_ids = fields.One2many(related='picking_id.batch_id.picking_ids')
