# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from werkzeug import urls

from odoo import _, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_mercado_pago.controllers.main import MercadoPagoController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, rendering_values):
        """ Override of payment to return Mercado Pago specific rendering values.

        Note: self.ensure_one() from `_get_rendering_values`

        :param dict rendering_values: The generic rendering values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """

        res = super()._get_specific_rendering_values(rendering_values)
        if self.provider != 'mercado_pago':
            return res

        # Create a preference to get a redirection url of Mercado Pago to initiate
        # the payment flow
        preference = self._mercado_pago_create_preference(self.reference)

        if self.acquirer_id.state == "test":
            redirection_url = preference.get("sandbox_init_point", '')
        else:
            redirection_url = preference.get("init_point", '')

        if redirection_url == '':
            raise ValidationError(
                "Mercado Pago: " + _("no redirection url returned, cannot redirect.")
            )

        return {
            'api_url': redirection_url,
        }

    def _mercado_pago_create_preference(self, external_reference, items=None, **kwargs):
        """
        Create a preference for mercado pago to get the redirection url to begin the
        payment flow.
        Preferences are items or payments that can be created from MP, they answer with a
        redirection url to pay such item.

        :param external_reference: the transaction reference to sync with MP server
        :param items: items to pay for, e.g. a product, if None is given we will simply generate
                      a payment

        :return: a dict with the answer of MP, in particular the redirection url
        :rtype: dict
        """

        # The back_url is a dict with the redirection urls for MP to return to.
        back_url = ""
        if self.operation == "online_redirect":
            back_url = urls.url_join(
                self.get_base_url(),
                MercadoPagoController._url_checkout_return
            )

        back_urls = ({
                         "success": back_url,
                         "pending": back_url,
                         "failure": back_url,
                     }
                     if back_url != "" else {})

        # Url to which MP can send notifications.
        notification_url = urls.url_join(self.get_base_url(), MercadoPagoController._url_webhook)

        if items is None:
            items = [{
                "title": "Payment",
                "quantity": 1,
                "unit_price": self.amount,
                "currency_id": self.currency_id.name
            }]

        payer = {
            "name": self.partner_name or {},
            "email": self.partner_email or {},
            "phone": {
                "area_code": "",
                "number": self.partner_phone or "",
            },
            "address": {
                "zip_code": self.partner_zip or "",
                "street_name": self.partner_address or "",
                "street_number": "",
            },
        }

        data = {
            "auto_return": "all",
            "back_urls": back_urls,
            "notification_url": notification_url,
            "external_reference": external_reference,
            "payer": payer,
            "items": items,
            "statement_descriptor": "MERCADOPAGO",
            **kwargs
        }

        return self.acquirer_id._mercado_pago_make_request("/checkout/preferences", "POST", data)

    def _get_tx_from_notification_data(self, provider, notification_data):
        """ Override of payment to find the transaction based on Mercado Pago data.

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

        reference = notification_data.get('external_reference')
        if not reference:
            raise ValidationError(
                "Mercado Pago: " + _("Received data with missing merchant external reference")
            )

        tx = self.search([('reference', '=', reference), ('provider', '=', 'mercado_pago')])
        if not tx:
            raise ValidationError(
                "Mercado Pago: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Mercado Pago data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data build from information passed to the
                                       return route.
        :return: None
        :raise: ValidationError if inconsistent data was received
        """
        super()._process_notification_data(notification_data)
        if self.provider != 'mercado_pago':
            return

        # If the notification comes from the webhook then we have to fetch the data from MP
        if 'webhook_notification' in notification_data:
            notification_data = self.acquirer_id._mercado_pago_make_request(
                f"/v1/payments/{notification_data['payment_id']}", 'GET'
            )

        # Handle the notification data here and get the necessary values
        # this part should process the notification and alter self in dependency
        if 'status' not in notification_data:
            raise ValidationError(
                "Mercado Pago: " + _("No status was found in the notification data")
            )
        status = notification_data['status']

        # When the notification comes from the webhook there is no need to update the reference.
        if not self.acquirer_reference:
            self.acquirer_reference = notification_data['payment_id']

        if status in ['pending', 'in_process', 'in_mediation']:
            self._set_pending()
        elif status == 'approved':
            self._set_done()
        elif status == 'authorized':
            self._set_authorize()
        elif status == 'rejected':
            pass
        elif status == 'cancelled':
            self._set_canceled()
        elif status in ['refunded', 'charged_back'] and self.operation == 'refund':
            self._set_done()
        else:
            self._set_error(
                "Mercado Pago: " + _("Received data with invalid status: %s", status)
            )
