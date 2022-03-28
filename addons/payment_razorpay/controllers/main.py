# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import hmac
import logging
import pprint
from hashlib import sha256

from odoo import http
from odoo.http import request

from werkzeug.exceptions import Forbidden
from odoo.exceptions import ValidationError

from odoo.addons.payment_razorpay.const import HANDLED_WEBHOOK_EVENTS

_logger = logging.getLogger(__name__)


class RazorpayController(http.Controller):
    _return_url = '/payment/razorpay/capture'
    _webhook_url = '/payment/razorpay/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['POST'], csrf=False)
    def razorpay_capture(self, **data):

        if data.get('razorpay_payment_id'):
            PaymentTransaction = request.env['payment.transaction']
            PaymentAcquirer = request.env['payment.acquirer']
            razorpay_payment_id = data.get('razorpay_payment_id')

            path = "/payments/%s" % razorpay_payment_id
            response = PaymentTransaction._razorpay_send_request(path=path, method="get")
            _logger.info('Razorpay: payment status %s', pprint.pformat(response))

            payment_acquirer = PaymentAcquirer.search([('provider', '=', 'razorpay')], limit=1)

            if payment_acquirer.capture_manually and response.get('status') != 'captured':
                reference = response.get('notes', {}).get('order_id', False)
                response = PaymentTransaction._create_razorpay_capture(reference, razorpay_payment_id)
                _logger.info('Razorpay: create capture %s', pprint.pformat(response))

            tx_sudo = PaymentTransaction._get_tx_from_notification_data(
                'razorpay', response
            )
            if response.get('id') and tx_sudo:

                key_secret = tx_sudo.acquirer_id._get_razorpay_secret_key()
                self._verify_signature(data, key_secret)

                _logger.info('Razorpay: entering form_feedback with post data %s', pprint.pformat(response))
                tx_sudo._handle_notification_data('razorpay', response)
        return '/payment/status'

    @staticmethod
    def _verify_signature(data, key_secret):
        """ Check that the received signature matches the expected one."""

        # Retrieve the received signature from the data
        razorpay_signature = str(data['razorpay_signature'])
        if not razorpay_signature:
            _logger.warning("received data with missing signature")
            raise Forbidden()

        if data.get('razorpay_subscription_id', False):
            body = "{}|{}".format(data.get('razorpay_payment_id'), data.get('razorpay_subscription_id'))
        else:
            body = "{}|{}".format(data.get('razorpay_order_id'), data.get('razorpay_payment_id'))

        key_secret = bytes(key_secret, 'utf-8')
        body = bytes(body, 'utf-8')

        dig = hmac.new(key=key_secret, msg=body, digestmod=sha256)

        generated_signature = dig.hexdigest()
        result = hmac.compare_digest(generated_signature, razorpay_signature)

        if not result:
            _logger.warning("received data with invalid signature")
            raise Forbidden()
        return result

    @http.route(_webhook_url, type='json', auth='public')
    def razorpay_webhook(self):
        """ Process the notification data sent by Razorpay to the webhook.

        :return: An empty string to acknowledge the notification
        :rtype: str
        """
        event = json.loads(request.httprequest.data)
        _logger.info("notification received from Razorpay with data:\n%s", pprint.pformat(event))
        try:
            if event['event'] in HANDLED_WEBHOOK_EVENTS:
                intent = event['event'] # subscription.charged, depending on the flow
                # TO DO - PPR
        except ValidationError:  # Acknowledge the notification to avoid getting spammed
            _logger.exception("unable to handle the notification data; skipping to acknowledge")
        return ''
