# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PaymentRefundWizard(models.TransientModel):
    _name = 'payment.refund.wizard'
    _description = "Payment Refund Wizard"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res_model = self.env.context.get('active_model')
        res_id = self.env.context.get('active_id')
        if res_model and res_id:
            res.update(
                self.env[res_model].browse(res_id)._get_payment_refund_wizard_values()
            )

    transaction_id = fields.Many2one(
        comodel_name='payment.transaction',
        string="Payment Transaction",
        required=True,
    )
    payment_amount = fields.Monetary(string="Payment Amount", default=0)
    refunded_amount = fields.Monetary(string="Refunded Amount", compute='_compute_refunded_amount')
    amount_available_for_refund = fields.Monetary(string="Maximum Refund Allowed", default=0)
    amount_to_refund = fields.Monetary(
        string="Refund Amount", compute='_compute_amount_to_refund', store=True, readonly=False
    )
    currency_id = fields.Many2one(string="Currency", related='transaction_id.currency_id')
    support_refund = fields.Selection(related='transaction_id.acquirer_id.support_refund')
    has_pending_refund = fields.Boolean(
        string="Has a pending refund", compute='_compute_has_pending_refund'
    )

    @api.constrains('amount_to_refund')
    def _check_amount_to_refund_within_boundaries(self):
        for wizard in self:
            if not 0 < wizard.amount_to_refund <= wizard.amount_available_for_refund:
                raise ValidationError(_(
                    "The amount to be refunded must be positive and cannot be superior to %s.",
                    wizard.amount_available_for_refund
                ))

    @api.depends('amount_available_for_refund')
    def _compute_refunded_amount(self):
        for wizard in self:
            wizard.refunded_amount = wizard.payment_amount - wizard.amount_available_for_refund

    @api.depends('amount_available_for_refund')
    def _compute_amount_to_refund(self):
        """ Set the default amount to refund to the amount available for refund. """
        for wizard in self:
            wizard.amount_to_refund = wizard.amount_available_for_refund

    @api.depends('transaction_id')  # To always trigger the compute
    def _compute_has_pending_refund(self):
        for wizard in self:
            pending_refunds_count = self.env['payment.transaction'].search_count([
                ('source_transaction_id', '=', wizard.transaction_id.id),
                ('operation', '=', 'refund'),
                ('state', 'in', ['draft', 'pending', 'authorized']),
            ])
            wizard.has_pending_refund = pending_refunds_count > 0

    def action_refund(self):
        for wizard in self:
            wizard.transaction_id.action_refund(amount_to_refund=wizard.amount_to_refund)
