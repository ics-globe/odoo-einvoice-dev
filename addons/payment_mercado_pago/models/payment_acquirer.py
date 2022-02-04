# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests
import pprint
from werkzeug import urls

from odoo import _, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('mercado_pago', "Mercado Pago")], ondelete={'mercado_pago': 'set default'})
    mercado_pago_public_key = fields.Char(
        string="Public Key", help="The key for frontend uses of Mercado Pago.",
        required_if_provider='mercado_pago')
    mercado_pago_secret_key = fields.Char(string="Private Key",
                                          help="Secret Key for processing payment related tasks.",
                                          required_if_provider='mercado_pago',
                                          groups='base.group_system')

    def _mercado_pago_make_request(self, endpoint, method, data=None):

        self.ensure_one()

        headers = {
            'Authorization': f"Bearer {self.mercado_pago_secret_key}",
            'Content-Type': 'application/json'
        }
        request_url = urls.url_join("https://api.mercadopago.com", endpoint)

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
                                      request_url, data)

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

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'mercado_pago':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_mercado_pago.payment_method_mercado_pago').id

    def _neutralize(self):
        super()._neutralize()
        self._neutralize_fields('mercado_pago', [
            'mercado_pago_public_key',
            'mercado_pago_secret_key',
        ])
