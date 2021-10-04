# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import fields, models

class PaymentToken(models.Model):
    _inherit = 'payment.token'

    # State must correspond to the existing state of payment transaction. 'Draft' and 'Authorized'
    # are ignored since payment by token are captured immediately and it is not probable to have a
    # token that creates 'Draft' transactions.
    test_state = fields.Selection(string="Test Status",
        selection=[('pending', "Pending"), ('done', "Confirmed"), ('cancel', "Canceled"),
                   ('error', "Error")],
        help="This status will be applied to all testing transactions made with this token on the "
             "'test' acquirer",
    )
