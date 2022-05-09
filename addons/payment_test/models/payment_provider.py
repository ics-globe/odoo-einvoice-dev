# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('test', 'Test')], ondelete={'test': 'set default'})

    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to hide the credentials page.

        :return: None
        """
        super()._compute_view_configuration_fields()
        self.filtered(lambda pro: pro.code == 'test').show_credentials_page = False

    @api.constrains('state', 'code')
    def _check_provider_state(self):
        if self.filtered(lambda pro: pro.code == 'test' and pro.state not in ('test', 'disabled')):
            raise UserError(_("Test providers should never be enabled."))

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.code != 'test':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_test.payment_method_test').id
