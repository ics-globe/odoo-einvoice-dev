# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests
import pprint
from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

ALLOWED_CURRENCIES = [
    'USD',  # US Dollars
    'ARS',  # Argentinian Peso
    'BRL',  # Real
    'CLP',  # Chilean Peso
    'CLF',  # Fomento Unity
    'MXN',  # Mexican Peso
    'COP',  # Colombian Peso
    'CRC',  # Colon
    'CUC',  # Cuban Convertible Peso
    'CUP',  # Cuban Peso
    'DOP',  # Dominican Peso
    'GTQ',  # Guatemalan Quetzal
    'HNL',  # Lempira
    'NIO',  # Cordoba
    'PAB',  # Balboa
    'PEN',  # Sol
    'PYG',  # Guarani
    'UYU',  # Uruguayan Peso
    'VEF',  # Strong Bolivar
    'VES',  # Sovereign Bolivar
]

class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    mercado_pago_base_url = "https://api.mercadopago.com"

    provider = fields.Selection(
        selection_add=[('mercado_pago', "Mercado Pago")], ondelete={'mercado_pago': 'set default'})
    mercado_pago_access_token = fields.Char(string="Access Token",
                                            help="Access token for processing payment related "
                                                 "tasks.",
                                            required_if_provider='mercado_pago',
                                            groups='base.group_system')

    def _mercado_pago_make_request(self, endpoint, method, data=None):

        self.ensure_one()

        headers = {
            'Authorization': f"Bearer {self.mercado_pago_access_token}",
            'Content-Type': 'application/json'
        }

        request_url = urls.url_join(self.mercado_pago_base_url, endpoint)

        _logger.info("sending request to %s:\n%s\n%s", request_url, pprint.pformat(headers),
                     pprint.pformat(data or {}))

        try:
            response = requests.request(method, request_url, data=json.dumps(data), headers=headers,
                                        timeout=60)

            if not response.ok and 400 <= response.status_code < 500:
                # Mercado Pago errors have status in the 400s values
                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError:
                    _logger.exception("invalid API request at %s with data %s",
                                      request_url, pprint.pformat(data))

                    response = json.loads(response.content)

                    error_type = response.get('error', '')
                    error_msg = response.get('message', '')

                    raise ValidationError(
                        "Mercado Pago: " + _(
                            "The communication with the API failed.\n"
                            "Mercado Pago gave us the following info about the "
                            "problem:\n'%s': '%s'",
                            error_type, error_msg
                        )
                    )

            return json.loads(response.content)
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", request_url)
            raise ValidationError("Mercado Pago: " +
                                  _("Could not establish the connection to the API."))

    @api.model
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        """ Override of payment to unlist MP acquirers for unsupported currencies. """
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()

        if currency and currency.name not in ALLOWED_CURRENCIES:
            acquirers = acquirers.filtered(
                lambda a: a.provider != 'mercado_pago'
            )

        return acquirers

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'mercado_pago':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_mercado_pago.payment_method_mercado_pago').id

    def _neutralize(self):
        super()._neutralize()
        self._neutralize_fields('mercado_pago', [
            'mercado_pago_access_token',
        ])
