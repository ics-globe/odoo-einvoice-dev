from odoo import api, fields, models, tools, _

class PosConfig(models.Model):
    _inherit = 'pos.order'

    def action_invoice_order(self):
        print("it works")
