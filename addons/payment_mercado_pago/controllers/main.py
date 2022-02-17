# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class MercadoPagoController(http.Controller):

    _url_checkout_return = '/payment/mercado_pago/checkout_return'
    _url_webhook = '/payment/mercado_pago/webhook'

    @http.route(_url_checkout_return, type='http', auth='public', csrf=False)
    def mercado_pago_return_from_checkout(self, **data):
        """ Process the notification data sent by Mercado Pago after redirection from checkout.

        :param dict data: The GET params to retrieve the transaction
        """

        _logger.info("received notification data from Mercado Pago:\n%s", pprint.pformat(data))

        # Retrieve the tx based on the tx reference included in the return url
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'mercado_pago', data
        )

        self.verify_notification(data, tx_sudo)

        # Handle the notification data crafted with MP API objects
        tx_sudo._handle_notification_data('mercado_pago', data)

        # Redirect the user to the status page
        return request.redirect('/payment/status')

    @http.route(_url_webhook, type='json', auth='public')
    def mercado_pago_webhook(self):
        data = request.dispatcher.jsonrequest

        _logger.info("received notification data from Mercado Pago:\n%s", pprint.pformat(data))

        if 'type' in data and data['type'] == 'payment':
            # Payment creations are treated by the redirection to the checkout url.
            if data['action'] == 'payment.created':
                pass
            if data['action'] == 'payment.updated':
                # First verify the notification
                payment_id = data['data']['id']
                tx_sudo = request.env['payment.transaction'].sudo().search(
                    [('provider', '=', 'mercado_pago'),
                     ('acquirer_reference', '=', payment_id)]
                )

                if not tx_sudo:
                    _logger.warning(
                        "Mercado Pago: received invalid notification:\n%s", pprint.pformat(data)
                    )

                self.verify_notification({'payment_id': payment_id}, tx_sudo)

                tx_sudo._handle_notification_data(
                    'mercado_pago',
                    {'webhook_notification': True, 'payment_id': payment_id}
                )

        return '[accepted]'

    def verify_notification(self, data, tx_sudo):
        """
        Verify that the notification received comes from MP.

        MP does not provide a signature to its notification, but it provides a payment id
        that we can then use to fetch the transaction details from MP and verify that match
        the transaction details on our side.

        :param data: dict with the data from the MP notification
        :param tx_sudo: transaction against to which compare the information from MP

        :return: nothing, raises a Forbidden it the transaction is a mismatch
        """

        acquirer_mp = request.env['payment.acquirer'].sudo().search(
            [('provider', '=', 'mercado_pago')]
        )

        # Retrieve the payment data from MP and verify that it match the transaction data in odoo
        payment_id = data['payment_id']
        payment_data = acquirer_mp._mercado_pago_make_request(f'/v1/payments/{payment_id}', 'GET')

        payment_title = payment_data['additional_info']['items'][0]['title']
        payment_amount = float(payment_data['additional_info']['items'][0]['unit_price'])
        payment_external_reference = payment_data['external_reference']

        if (
                payment_title != 'Payment'
                or float_compare(payment_amount, tx_sudo.amount, tx_sudo.currency_id.rounding) != 0
                or payment_external_reference != tx_sudo.reference
        ):
            _logger.warning("Mercado Pago: received notification with invalid payment id.")
            raise Forbidden()
