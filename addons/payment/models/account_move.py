# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    transaction_ids = fields.Many2many(
        string="Transactions", comodel_name='payment.transaction',
        relation='account_invoice_transaction_rel', column1='invoice_id', column2='transaction_id',
        readonly=True, copy=False)
    authorized_transaction_ids = fields.Many2many(
        string="Authorized Transactions", comodel_name='payment.transaction',
        compute='_compute_authorized_transaction_ids', readonly=True, copy=False)

    @api.depends('transaction_ids')
    def _compute_authorized_transaction_ids(self):
        for invoice in self:
            invoice.authorized_transaction_ids = invoice.transaction_ids.filtered(
                lambda tx: tx.state == 'authorized'
            )

    def get_portal_last_transaction(self):
        self.ensure_one()
        return self.with_context(active_test=False).transaction_ids._get_last()

    def payment_action_capture(self):
        if not any(self.authorized_transaction_ids.acquirer_id.support_capture):
            self.authorized_transaction_ids.action_capture()
        else:
            self.ensure_one()
            operations = ['online_redirect', 'online_direct', 'online_token', 'offline']
            return {
                'name': _("Capture"),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'payment.capture.wizard',
                'target': 'new',
                'context': {
                    'active_ids': self.transaction_ids.filtered(
                        lambda tx: tx.state in ['authorized', 'done'] and tx.operation in operations
                    ).ids,  # In case of multiple partial captures, some tx may already be done
                    'active_model': 'payment.transaction'
                },
            }

    def payment_action_void(self):
        self.authorized_transaction_ids.action_void()

    def action_view_payment_transactions(self):
        action = self.env['ir.actions.act_window']._for_xml_id('payment.action_payment_transaction')

        if len(self.transaction_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.transaction_ids.id
            action['views'] = []
        else:
            action['domain'] = [('id', 'in', self.transaction_ids.ids)]

        return action
