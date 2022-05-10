from odoo import api, fields, models, tools, _

class PosConfig(models.Model):
    _inherit = 'pos.config'

    default_customer = fields.Many2one('res.partner', string='Default Customer')
    default_product = fields.Many2one('product.product', string='Default Product')
