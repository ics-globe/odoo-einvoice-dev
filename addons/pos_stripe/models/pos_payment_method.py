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

    def _get_stripe_endpoints(self):
        return {
            'terminal_request': 'https://terminal-api-%s.adyen.com/async',
        }

    def _is_write_forbidden(self, fields):
        whitelisted_fields = set(('stripe_latest_response', 'stripe_latest_diagnosis'))
        return super(PosPaymentMethod, self)._is_write_forbidden(fields - whitelisted_fields)

    def _stripe_diagnosis_request_data(self, pos_config_name):
        service_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        return {
            "SaleToPOIRequest": {
                "MessageHeader": {
                    "ProtocolVersion": "3.0",
                    "MessageClass": "Service",
                    "MessageCategory": "Diagnosis",
                    "MessageType": "Request",
                    "ServiceID": service_id,
                    "SaleID": pos_config_name,
                    "POIID": self.stripe_serial_number,
                },
                "DiagnosisRequest": {
                    "HostDiagnosisFlag": False
                }
            }
        }

    def get_latest_stripe_status(self, pos_config_name):
        self.ensure_one()

        # Poll the status of the terminal if there's no new
        # notification we received. This is done so we can quickly
        # notify the user if the terminal is no longer reachable due
        # to connectivity issues.
        self.proxy_stripe_request(self._stripe_diagnosis_request_data(pos_config_name))

        latest_response = self.sudo().stripe_latest_response
        latest_response = json.loads(latest_response) if latest_response else False

        return {
            'latest_response': latest_response,
            'last_received_diagnosis_id': self.sudo().stripe_latest_diagnosis,
        }

    def proxy_stripe_request(self, data, operation=False):
        ''' Necessary because stripe's endpoints don't have CORS enabled '''
        if data['SaleToPOIRequest']['MessageHeader']['MessageCategory'] == 'Payment': # Clear only if it is a payment request
            self.sudo().stripe_latest_response = ''  # avoid handling old responses multiple times

        if not operation:
            operation = 'terminal_request'

        return self._proxy_stripe_request_direct(data, operation)

    def _proxy_stripe_request_direct(self, data, operation):
        self.ensure_one()
        TIMEOUT = 10

        payment_acquirer_stripe = self.env['payment.acquirer'].search([('provider', '=', 'stripe')], limit=1)
        payment_acquirer_stripe._get_stripe_secret_key()

        _logger.info('request to stripe\n%s', pprint.pformat(data))

        environment = 'test' if self.stripe_test_mode else 'live'
        endpoint = self._get_stripe_endpoints()[operation] % environment
        headers = {
            'x-api-key': self.stripe_api_key,
        }
        req = requests.post(endpoint, json=data, headers=headers, timeout=TIMEOUT)

        # Authentication error doesn't return JSON
        if req.status_code == 401:
            return {
                'error': {
                    'status_code': req.status_code,
                    'message': req.text
                }
            }

        return req.json()

    @api.model
    def stripe_connection_token(self):
        TIMEOUT = 10
        payment_acquirer_stripe = self.env['payment.acquirer'].search([('provider', '=', 'stripe')], limit=1)

        endpoint = 'https://api.stripe.com/v1/terminal/connection_tokens'

        if not payment_acquirer_stripe.stripe_secret_key:
            raise ValidationError(_('Stripe connect empty.'))

        req = requests.post(endpoint, auth=(payment_acquirer_stripe.stripe_secret_key, ''), timeout=TIMEOUT)

        if req.status_code == 401:
            return {
                'error': {
                    'status_code': req.status_code,
                    'message': req.text
                }
            }

        print(req.json())
        return req.json()
