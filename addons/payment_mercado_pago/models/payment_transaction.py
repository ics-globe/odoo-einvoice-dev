# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_mercado_pago.controllers.main import MercadoPagoController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    mercado_pago_payment_intent = fields.Char(string="Mercado Pago Payment Intent ID", readonly=True)

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Stripe-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """

        res = super()._get_specific_processing_values(processing_values)
        if self.provider != 'mercado_pago' or self.operation == 'online_token':
            return res

        return {
            'public_key': self.acquirer_id.mercado_pago_public_key,
        }

    def _mercado_pago_create_customer(self):
        """ Create and return a Customer.

        :return: The Customer
        :rtype: dict
        """
        customer = self.acquirer_id._mercado_pago_make_request(
            'customers', payload={
                'address[city]': self.partner_city or None,
                'address[country]': self.partner_country_id.code or None,
                'address[line1]': self.partner_address or None,
                'address[postal_code]': self.partner_zip or None,
                'address[state]': self.partner_state_id.name or None,
                'description': f'Odoo Partner: {self.partner_id.name} (id: {self.partner_id.id})',
                'email': self.partner_email,
                'name': self.partner_name,
                'phone': self.partner_phone or None,
            }
        )
        return customer

    def _send_payment_request(self):
        """ Override of payment to send a payment request to Stripe with a confirmed PaymentIntent.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        super()._send_payment_request()
        if self.provider != 'mercado_pago':
            return

        # Make the payment request to Stripe
        if not self.token_id:
            raise UserError("Mercado Pago: " + _("The transaction is not linked to a token."))

        payment_intent = self._mercado_pago_create_payment_intent()
        feedback_data = {'reference': self.reference}
        MercadoPagoController._include_payment_intent_in_notification_data(payment_intent, feedback_data)
        _logger.info(
            "payment request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(feedback_data)
        )
        self._handle_notification_data('mercado_pago', feedback_data)

    def _mercado_pago_create_payment_intent(self):
        """ Create and return a PaymentIntent.

        Note: self.ensure_one()

        :return: The Payment Intent
        :rtype: dict
        """
        if not self.token_id.mercado_pago_payment_method:  # Pre-SCA token -> migrate it
            self.token_id._mercado_pago_sca_migrate_customer()

        response = self.acquirer_id._mercado_pago_make_request(
            'payment_intents',
            payload={
                'amount': payment_utils.to_minor_currency_units(self.amount, self.currency_id),
                'currency': self.currency_id.name.lower(),
                'confirm': True,
                'customer': self.token_id.acquirer_ref,
                'off_session': True,
                'payment_method': self.token_id.mercado_pago_payment_method,
                'description': self.reference,
            },
            offline=self.operation == 'offline',
        )
        if 'error' not in response:
            payment_intent = response
        else:  # A processing error was returned in place of the payment intent
            error_msg = response['error'].get('message')
            self._set_error("Mercado Pago: " + _(
                "The communication with the API failed.\n"
                "Mercado Pago gave us the following info about the problem:\n'%s'", error_msg
            ))  # Flag transaction as in error now as the intent status might have a valid value
            payment_intent = response['error'].get('payment_intent')  # Get the PI from the error

        return payment_intent

    def _get_tx_from_notification_data(self, provider, notification_data):
        """ Override of payment to find the transaction based on Stripe data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider, notification_data)
        if provider != 'mercado_pago' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference')
        if not reference:
            raise ValidationError("Mercado Pago: " + _("Received data with missing merchant reference"))

        tx = self.search([('reference', '=', reference), ('provider', '=', 'mercado_pago')])
        if not tx:
            raise ValidationError(
                "Mercado Pago: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Adyen data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data build from information passed to the
                                       return route. Depending on the operation of the transaction,
                                       the entries with the keys 'payment_intent', 'charge',
                                       'setup_intent' and 'payment_method' can be populated with
                                       their corresponding Stripe API objects.
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_notification_data(notification_data)
        if self.provider != 'mercado_pago':
            return

        if 'charge' in notification_data:
            self.acquirer_reference = notification_data['charge']['id']

        # Handle the intent status
        if self.operation == 'validation':
            intent_status = notification_data.get('setup_intent', {}).get('status')
        else:  # 'online_redirect', 'online_token', 'offline'
            intent_status = notification_data.get('payment_intent', {}).get('status')
        if not intent_status:
            raise ValidationError(
                "Mercado Pago: " + _("Received data with missing intent status.")
            )

        if intent_status in INTENT_STATUS_MAPPING['draft']:
            pass
        elif intent_status in INTENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif intent_status in INTENT_STATUS_MAPPING['done']:
            if self.tokenize:
                self._mercado_pago_tokenize_from_notification_data(notification_data)
            self._set_done()
        elif intent_status in INTENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        else:  # Classify unknown intent statuses as `error` tx state
            _logger.warning(
                "received invalid payment status (%s) for transaction with reference %s",
                intent_status, self.reference
            )
            self._set_error(
                "Mercado Pago: " + _("Received data with invalid intent status: %s", intent_status)
            )

    def _mercado_pago_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        :param dict notification_data: The notification data built with Stripe objects.
                                       See `_process_notification_data`.
        :return: None
        """
        if self.operation == 'online_redirect':
            payment_method_id = notification_data.get('charge', {}).get('payment_method')
            customer_id = notification_data.get('charge', {}).get('customer')
        else:  # 'validation'
            payment_method_id = notification_data.get('setup_intent', {}) \
                .get('payment_method', {}).get('id')
            customer_id = notification_data.get('setup_intent', {}).get('customer')
        payment_method = notification_data.get('payment_method')
        if not payment_method_id or not payment_method:
            _logger.warning(
                "requested tokenization from notification data with missing payment method"
            )
            return

        if payment_method.get('type') != 'card':
            # Only 'card' payment methods can be tokenized. This case should normally not happen as
            # non-recurring payment methods are not shown to the customer if the "Save my payment
            # details checkbox" is shown. Still, better be on the safe side..
            _logger.warning("requested tokenization of non-recurring payment method")
            return

        token = self.env['payment.token'].create({
            'acquirer_id': self.acquirer_id.id,
            'name': payment_utils.build_token_name(payment_method['card'].get('last4')),
            'partner_id': self.partner_id.id,
            'acquirer_ref': customer_id,
            'verified': True,
            'mercado_pago_payment_method': payment_method_id,
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })
        _logger.info(
            "created token with id %(token_id)s for partner with id %(partner_id)s from "
            "transaction with reference %(ref)s",
            {
                'token_id': token.id,
                'partner_id': self.partner_id.id,
                'ref': self.reference,
            },
        )
