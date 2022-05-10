from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        res = super(PosSession, self)._validate_session(balancing_account, amount_to_balance, bank_payment_method_diffs)
        orders_without_customer = self.env['pos.order'].search([('session_id', '=', f'{self.name}'), ('partner_id', '=', None)])
        general_customer = self.env.ref('l10n_mx_pos.res_partner_general_customer_mx')
        for order in orders_without_customer:
            order.write({
                'partner_id': general_customer
            })
        return res
