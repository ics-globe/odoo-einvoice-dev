# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import requests
import json
import logging
import pprint

from odoo import  api, models, _
from odoo.exceptions import ValidationError
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Adyen-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider != 'razorpay':
            return res
        converted_amount = payment_utils.to_minor_currency_units(processing_values.get('amount'), self.currency_id)
        data = {
            'currency': self.currency_id.name,
            'amount': converted_amount,
        }
        response = self._razorpay_send_request(path='/orders', data=data, method="post")
        _logger.info('Razorpay: entering form_feedback with post data %s', pprint.pformat(response))

        processing_values.update({
            "currency": self.currency_id.name,
            'amount': converted_amount,
            'key': self.acquirer_id._get_razorpay_key(),
            'order_id': response.get('id'),
            'prefill': {
                'name': self.partner_name,
                'contact': self.partner_phone,
                'email': self.partner_email,
            },
            'notes': {
                'order_id': processing_values.get('reference'),
            },
            "theme": {
                "color": 'orange' if self.acquirer_id.state == 'test' else 'green'
            },
        })
        return processing_values

    def _get_tx_from_notification_data(self, provider, notification_data):
        """ Override of payment to find the transaction based on Buckaroo data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict notification_data: The normalized notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider, notification_data)
        if provider != 'razorpay' or len(tx) == 1:
            return tx
        reference = notification_data.get('notes', {}).get('order_id')

        tx = self.search([('reference', '=', reference), ('provider', '=', 'razorpay')])
        if not tx:
            raise ValidationError(
                "razorpay: " + _("No transaction found matching reference %s.", reference)
            )

        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Razorpay data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider != 'razorpay':
            return

        status = notification_data.get('status')
        self.write({'acquirer_reference': notification_data.get('id')})

        if status == 'captured':
            self._set_done()
        elif status == 'authorized':
            self._set_authorized()
        elif status in notification_data.get('reason'):
            self._set_canceled()
            self._set_error(_(
                "An error occurred during processing of your payment (code %s). Please try again.",
                notification_data.get('error'),
            ))

    def _razorpay_send_request(self, path, method, data=None,):
        headers = {'Content-type': 'application/json'}
        base_url = "https://api.razorpay.com/v1"
        request_url = "%s%s" % (base_url, path)
        payment_response = {}

        acquirer = self.acquirer_id
        if not acquirer:
            acquirer = self.env['payment.acquirer'].search([('provider', '=', 'razorpay')], limit=1)
        try:
            payment_response = getattr(requests, method)(
                request_url,
                auth=(acquirer._get_razorpay_key(), acquirer._get_razorpay_secret_key()),
                data=json.dumps(data),
                headers=headers)
            payment_response = payment_response.json()
        except Exception as e:
            _logger.warning(
                "received invalid plan or subscription status (%s)", e
            )
            raise e

        return payment_response

    @api.model
    def _create_razorpay_capture(self, reference, payment_id):
        transaction = self.search([('reference', '=', reference)])
        amount = payment_utils.to_minor_currency_units(transaction.amount, transaction.currency_id)
        charge_data = {'amount': amount}
        path = "/payments/%s/capture" % payment_id
        try:
            response = self._razorpay_send_request(path=path, data=charge_data, method="post")
        except Exception as e:
            raise e
        return response
