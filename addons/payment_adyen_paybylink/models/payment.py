# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import requests

from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_adyen_paybylink.const import API_ENDPOINT_VERSIONS


_logger = logging.getLogger(__name__)


class AcquirerAdyenPayByLink(models.Model):
    _inherit = 'payment.acquirer'

    adyen_api_key = fields.Char(
        string='API Key', help="The API key of the webservice user", required_if_provider='adyen',
        groups='base.group_user'
    )
    adyen_hmac_key = fields.Char(
        string="HMAC Key", help="The HMAC key of the webhook", required_if_provider='adyen',
        groups='base.group_user'
    )
    adyen_checkout_api_url = fields.Char(
        string="Checkout API URL", help="The base URL for the Checkout API endpoints",
        required_if_provider='adyen',
    )
    # We set a default for the now unused key fields rather than making them not required to avoid
    # the error log at DB init when the ORM tries to set the 'NOT NULL' constraint on those fields.
    adyen_skin_code = fields.Char(default="Do not use this field")
    adyen_skin_hmac_key = fields.Char(default="Do not use this field")

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            self._adyen_trim_api_urls(values)
        return super().create(values_list)

    def write(self, values):
        self._adyen_trim_api_urls(values)
        # We set a default for the now unused key fields rather than making them not required to avoid
        # the error log at DB init when the ORM tries to set the 'NOT NULL' constraint on those fields.
        values.update(
            adyen_skin_code="Do not use this field",
            adyen_skin_hmac_key="Do not use this field",
        )
        return super().write(values)

    @api.model
    def _adyen_trim_api_urls(self, values):
        """ Remove the version and the endpoint from the url of Adyen API fields.
        :param dict values: The create or write values
        :return: None
        """
        for field_name in ('adyen_checkout_api_url'):
            if values.get(field_name):  # Test the value in case we're duplicating an acquirer
                values[field_name] = re.sub(r'[vV]\d+(/.*)?', '', values[field_name])

    def adyen_form_generate_values(self, values):
        base_url = self.get_base_url()

        paymentAmount = self._adyen_convert_amount(values['amount'], values['currency'])
        adyen_paybylink_data = {
            'reference': values['reference'],
            'amount': {
                'value': '%d' % paymentAmount,
                'currency': values['currency'] and values['currency'].name or '',
            },
            'merchantAccount': self.adyen_merchant_account,
            'shopperLocale': values.get('partner_lang', ''),
            'returnUrl': urls.url_join(base_url, '/payment/process'),
            'shopperEmail': values.get('partner_email') or values.get('billing_partner_email') or '',
        }

        values['adyen_link'] = self.adyen_get_paybylink(adyen_paybylink_data)

        return values

    def adyen_get_form_action_url(self):
        self.ensure_one()
        return False

    def adyen_get_paybylink(self, data):
        paybylink_response = self._adyen_make_request(
            url_field_name='adyen_checkout_api_url',
            endpoint='/paymentLinks',
            payload=data,
        )
        return paybylink_response['url']

    def _adyen_make_request(
        self, url_field_name, endpoint, endpoint_param=None, payload=None, method='POST'
    ):
        """ Make a request to Adyen API at the specified endpoint.
        Note: self.ensure_one()
        :param str url_field_name: The name of the field holding the base URL for the request
        :param str endpoint: The endpoint to be reached by the request
        :param str endpoint_param: A variable required by some endpoints which are interpolated with
                                   it if provided. For example, the acquirer reference of the source
                                   transaction for the '/payments/{}/refunds' endpoint.
        :param dict payload: The payload of the request
        :param str method: The HTTP method of the request
        :return: The JSON-formatted content of the response
        :rtype: dict
        :raise: ValidationError if an HTTP error occurs
        """

        def _build_url(_base_url, _version, _endpoint):
            """ Build an API URL by appending the version and endpoint to a base URL.
            The final URL follows this pattern: `<_base>/V<_version>/<_endpoint>`.
            :param str _base_url: The base of the url prefixed with `https://`
            :param int _version: The version of the endpoint
            :param str _endpoint: The endpoint of the URL.
            :return: The final URL
            :rtype: str
            """
            _base = _base_url.rstrip('/')  # Remove potential trailing slash
            _endpoint = _endpoint.lstrip('/')  # Remove potential leading slash
            return f'{_base}/V{_version}/{_endpoint}'

        self.ensure_one()

        base_url = self[url_field_name]  # Restrict request URL to the stored API URL fields
        version = API_ENDPOINT_VERSIONS[endpoint]
        endpoint = endpoint if not endpoint_param else endpoint.format(endpoint_param)
        url = _build_url(base_url, version, endpoint)
        headers = {'X-API-Key': self.adyen_api_key}
        try:
            response = requests.request(method, url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", url)
            raise ValidationError("Adyen: " + _("Could not establish the connection to the API."))
        except requests.exceptions.HTTPError as error:
            _logger.exception(
                "invalid API request at %s with data %s: %s", url, payload, error.response.text
            )
            raise ValidationError("Adyen: " + _("The communication with the API failed."))
        return response.json()


class TxAdyen(models.Model):
    _inherit = 'payment.transaction'

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _adyen_form_get_tx_from_data(self, data):
        reference, pspReference = data.get('merchantReference'), data.get('pspReference')
        if not reference or not pspReference:
            error_msg = _(
                'Adyen: received data with missing reference (%s) or missing pspReference (%s)'
            ) % (reference, pspReference)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use pspReference ?
        tx = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = _('Adyen: received data for reference %s') % (reference)
            if not tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        return tx

    def _adyen_form_get_invalid_parameters(self, data):
        """ Override of form_get_invalid_parameters

        The implementation of pay by link doesn't need to check for invalid parameters
        """
        return []
