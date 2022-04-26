# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
import pprint
import random
import requests
import string
from werkzeug.exceptions import Forbidden

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.addons.payment_stripe.models.payment_acquirer import PaymentAcquirer

_logger = logging.getLogger(__name__)

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super(PosPaymentMethod, self)._get_payment_terminal_selection() + [('stripe', 'Stripe')]

    # Stripe
    stripe_serial_number = fields.Char(help='[Serial number], for example: WSC513105011295', copy=False)
    stripe_location_id = fields.Char(string="Stripe location ID", help='', copy=False)
    stripe_test_mode = fields.Boolean(help='Run transactions in the test environment.')

    stripe_latest_response = fields.Char(help='Technical field used to buffer the latest asynchronous notification from Stripe.', copy=False, groups='base.group_erp_manager')
    stripe_latest_diagnosis = fields.Char(help='Technical field used to determine if the terminal is still connected.', copy=False, groups='base.group_erp_manager')

    @api.constrains('stripe_serial_number')
    def _check_stripe_serial_number(self):
        for payment_method in self:
            if not payment_method.stripe_serial_number:
                continue
            existing_payment_method = self.search([('id', '!=', payment_method.id),
                                                   ('stripe_serial_number', '=', payment_method.stripe_serial_number)],
                                                  limit=1)
            if existing_payment_method:
                raise ValidationError(_('Terminal %s is already used on payment method %s.')
                                      % (payment_method.stripe_serial_number, existing_payment_method.display_name))

    def _get_stripe_secret_key(self):
        stripe_secret_key = self.env['payment.acquirer'].search([('provider', '=', 'stripe')], limit=1).stripe_secret_key

        if not stripe_secret_key:
            raise ValidationError(_('Stripe connect empty.'))

        return stripe_secret_key

    @api.model
    def stripe_connection_token(self):
        TIMEOUT = 10

        endpoint = 'https://api.stripe.com/v1/terminal/connection_tokens'

        req = requests.post(endpoint, auth=(self._get_stripe_secret_key(), ''), timeout=TIMEOUT)

        if req.status_code == 401:
            return {
                'error': {
                    'status_code': req.status_code,
                    'message': req.text
                }
            }

        print(req.json())
        return req.json()

    @api.model
    def stripe_payment_intent(self, currency, amount):
        TIMEOUT = 10
        # For Terminal payments, the 'payment_method_types' parameter must include
        # 'card_present' and the 'capture_method' must be set to 'manual'

        endpoint = 'https://api.stripe.com/v1/payment_intents'

        data = ("currency=%s&amount=%s&payment_method_types[]=card_present&capture_method=manual") % (currency, int(amount * 100))
        req = requests.post(endpoint, data=data, auth=(self._get_stripe_secret_key(), ''), timeout=TIMEOUT)

        if req.status_code == 401:
            return {
                'error': {
                    'status_code': req.status_code,
                    'message': req.text
                }
            }

        print(req.json())
        return req.json()

    @api.model
    def stripe_capture_payment(self, paymentIntentId):
        TIMEOUT = 10

        endpoint = ('https://api.stripe.com/v1/payment_intents/%s/capture') % (paymentIntentId)

        req = requests.post(endpoint, auth=(self._get_stripe_secret_key(), ''), timeout=TIMEOUT)

        if req.status_code == 401:
            return {
                'error': {
                    'status_code': req.status_code,
                    'message': req.text
                }
            }

        print('stripe_capture_payment')
        print(req.json())
        return req.json()
