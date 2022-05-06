# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    journal_id = fields.Many2one(
        string="Payment Journal", comodel_name='account.journal',
        compute='_compute_journal_id', inverse='_inverse_journal_id',
        help="The journal in which the successful transactions are posted",
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]")

    #=== COMPUTE METHODS ===#

    def _compute_journal_id(self):
        for acquirer in self:
            payment_method = self.env['account.payment.method.line'].search([
                ('journal_id.company_id', '=', acquirer.company_id.id),
                ('code', '=', acquirer.provider)
            ], limit=1)
            if payment_method:
                acquirer.journal_id = payment_method.journal_id
            else:
                acquirer.journal_id = False

    def _inverse_journal_id(self):
        for acquirer in self:
            payment_method_line = self.env['account.payment.method.line'].search([
                ('journal_id.company_id', '=', acquirer.company_id.id),
                ('code', '=', acquirer.provider)
            ], limit=1)
            if acquirer.journal_id:
                if not payment_method_line:
                    default_payment_method_id = acquirer._get_default_payment_method_id()
                    existing_payment_method_line = self.env['account.payment.method.line'].search([
                        ('payment_method_id', '=', default_payment_method_id),
                        ('journal_id', '=', acquirer.journal_id.id)
                    ], limit=1)
                    if not existing_payment_method_line:
                        self.env['account.payment.method.line'].create({
                            'payment_method_id': default_payment_method_id,
                            'journal_id': acquirer.journal_id.id,
                        })
                else:
                    payment_method_line.journal_id = acquirer.journal_id
            elif payment_method_line:
                payment_method_line.unlink()

    def _get_default_payment_method_id(self):
        self.ensure_one()
        return self.env.ref('account.account_payment_method_manual_in').id

    #=== BUSINESS METHODS ===#

    def _get_validation_currency(self):
        """ Get the currency of the transfer in a payment method validation operation.

        For an acquirer to support tokenization, it must override this method and return the
        currency to be used in a payment method validation operation *if the validation amount is
        not null*.

        Note: self.ensure_one()

        :return: The validation currency
        :rtype: recordset of `res.currency`
        """
        self.ensure_one()
        return self.journal_id.currency_id or super()._get_validation_currency()
