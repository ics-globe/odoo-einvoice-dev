# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.payment_razorpay.const import SUPPORTED_CURRENCIES

class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('razorpay', "Razorpay")], ondelete={'razorpay': 'set default'})
    razorpay_key_id = fields.Char(string='Key ID', required_if_provider='razorpay', groups='base.group_user')
    razorpay_key_secret = fields.Char(string='Key Secret', required_if_provider='razorpay', groups='base.group_user')

    def _get_razorpay_key(self):
        """ Return the razorpay key for Razorpay.

        Note: This method is overridden by the internal module responsible for Razorpay Connect.

        :return: The razorpay key
        :rtype: str
        """
        return self.razorpay_key_id

    def _get_razorpay_secret_key(self):
        """ Return the razorpay secret key and secret key for Razorpay.

        Note: This method is overridden by the internal module responsible for Razorpay Connect.

        :return: The razorpay secret key
        :rtype: str
        """
        return self.razorpay_key_secret

    @api.model
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        """ Override of payment to unlist razorpay acquirers for unsupported currencies. """
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name not in SUPPORTED_CURRENCIES:
            acquirers = acquirers.filtered(lambda a: a.provider != 'razorpay')

        return acquirers

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'razorpay':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_razorpay.payment_method_razorpay').id
