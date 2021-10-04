# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    capture_manually = fields.Boolean(related='acquirer_id.capture_manually')

    def action_done(self):
        """ Set the state of the transaction to 'done' if the provider is `Test`"""
        if self.provider != 'test':
            return

        notification_data = {'reference': self.reference, 'status': 'done'}
        self._handle_notification_data('test', notification_data)

    def action_authorized(self):
        """ Set the state of the transaction to 'authorized' if the provider is `Test`"""
        if self.provider != 'test':
            return

        notification_data = {'reference': self.reference, 'status': 'authorized'}
        self._handle_notification_data('test', notification_data)

    def action_cancel(self):
        """ Set the state of the transaction to 'canceled' if the provider is `Test`"""
        if self.provider != 'test':
            return

        notification_data = {'reference': self.reference, 'status': 'cancel'}
        self._handle_notification_data('test', notification_data)

    def action_error(self):
        """ Set the state of the transaction to 'error' if the provider is `Test`"""
        if self.provider != 'test':
            return

        notification_data = {'reference': self.reference, 'status': 'error'}
        self._handle_notification_data('test', notification_data)

    def _send_payment_request(self):
        """ Override of payment to simulate a payment request.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_payment_request()
        if self.provider != 'test':
            return

        if not self.token_id:
            raise UserError("Payment Test: " + _("The transaction is not linked to a token."))

        if self.acquirer_id.capture_manually and self.token_id.test_state == 'done':
            status = 'authorized'
        else:
            status = self.token_id.test_state

        notification_data = {'reference': self.reference, 'status': status}

        self._handle_notification_data('test', notification_data)

    def _send_refund_request(self, amount_to_refund=None, create_refund_transaction=True):
        """ Override of payment to simulate a refund

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to be refunded
        :param bool create_refund_transaction: Whether a refund transaction should be created
        :return: The refund transaction if any
        :rtype: recordset of `payment.transaction`
        """
        refund_tx = super()._send_refund_request(
            amount_to_refund=amount_to_refund, create_refund_transaction=create_refund_transaction
        )
        if self.provider != 'test':
            return refund_tx

        if refund_tx:
            notification_data = {'reference': refund_tx.reference, 'status': 'done'}
            refund_tx._handle_notification_data('test', notification_data)

        return refund_tx

    def _send_capture_request(self):
        """ Override of payment to simulate a capture request.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_capture_request()
        if self.provider != 'test':
            return

        notification_data = {'reference': self.reference, 'status': 'done'}

        self._handle_notification_data('test', notification_data)

    def _send_void_request(self):
        """ Override of payment to simulate a void request.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_void_request()
        if self.provider != 'test':
            return

        notification_data = {'reference': self.reference, 'status': 'cancel'}

        self._handle_notification_data('test', notification_data)

    def _get_tx_from_notification_data(self, provider, notification_data):
        """ Override of payment to find the transaction based on dummy data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict notification_data: The dummy notification data
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider, notification_data)
        if provider != 'test' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference')
        tx = self.search([('reference', '=', reference), ('provider', '=', 'test')])
        if not tx:
            raise ValidationError(
                "Test: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on dummy data.

        Note: self.ensure_one()

        :param dict notification_data: The dummy notification data
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_notification_data(notification_data)
        if self.provider != "test":
            return

        # Handle the status
        status = notification_data.get('status')
        if not status:
            raise ValidationError(
                "Test: " + _("Received fake data with missing status.")
            )

        # We create a token first to save the status selected on the payment form.
        if self.tokenize:
            self._test_tokenize_from_notification_data(notification_data)

        if status == 'draft':
            pass
        elif status == 'pending':
            self._set_pending()
        elif status == 'authorized':
            self._set_authorized()
        elif status == 'done':
            self._set_done()
            if self.operation == 'refund':
                self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        elif status == 'cancel':
            self._set_canceled()
        else:  # Simulate an error status
            self._set_error(
                "Test: " +
                _("You selected the following state on the checkout page: %s", status)
            )

    def _test_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        :param dict data: The notification data built with fake objects.
        See `_process_notification_data`.
        :return: None
        """
        payment_details_short = notification_data['customer_input']
        state = notification_data['status']
        token = self.env['payment.token'].create({
            'acquirer_id': self.acquirer_id.id,
            'name': payment_utils.build_token_name(payment_details_short=payment_details_short),
            'partner_id': self.partner_id.id,
            'acquirer_ref': 'fake acquirer reference',
            'verified': True,
            'test_state': state,
        })
        self.write({
            'token_id': token,
            'tokenize': False,
        })
        _logger.info(
            "created token with id %s for partner with id %s", token.id, self.partner_id.id
        )
