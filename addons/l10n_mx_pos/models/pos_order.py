from odoo import models
class PosConfig(models.Model):
    _inherit = 'pos.order'

    def action_invoice_order(self):
        for record in self:
            print(record.name)
            account_move = record._generate_pos_order_invoice()
            self.env['account.move'].browse(account_move['res_id']).write({
                'state' : 'draft',  # By default the invoice is posted
            })
        print("it works")
