# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_mercado_pago.controllers.main import MercadoPagoController
from odoo.addons.payment_mercado_pago.tests.common import MercadoPagoCommon


@tagged('post_install', '-at_install')
class MercadoPagoTest(MercadoPagoCommon, PaymentHttpCommon):

    def test_checkout_set_done_transaction(self):
        """Test the processing of transactions from the checkout"""
        tx = self.create_transaction(flow='redirect')

        mp_data = MercadoPagoCommon.NOTIFICATION_DATA
        mp_data['external_reference'] = self.reference
        mp_data['status'] = 'approved'

        url = self._build_url(MercadoPagoController._url_checkout_return)
        with patch(
                'odoo.addons.payment_mercado_pago.controllers.main.MercadoPagoController'
                '.verify_notification',
                return_values=True,
        ):
            self._make_http_post_request(url, data=mp_data)
        self.assertEqual(tx.state, 'done')

    def test_checkout_set_pending_transaction(self):
        """Test the processing of transactions from the checkout"""
        tx = self.create_transaction(flow='redirect')

        mp_data = MercadoPagoCommon.NOTIFICATION_DATA
        mp_data['external_reference'] = self.reference
        mp_data['status'] = 'pending'

        url = self._build_url(MercadoPagoController._url_checkout_return)
        with patch(
                'odoo.addons.payment_mercado_pago.controllers.main.MercadoPagoController'
                '.verify_notification',
                return_values=True,
        ):
            self._make_http_post_request(url, data=mp_data)
        self.assertEqual(tx.state, 'pending')

    def test_checkout_pending_confirm_webhook(self):
        """Test the processing of transactions from the checkout"""

        # create a transaction and set it up to 'pending'
        tx = self.create_transaction(flow='redirect')

        mp_data = MercadoPagoCommon.NOTIFICATION_DATA
        mp_data['external_reference'] = self.reference
        mp_data['status'] = 'pending'

        url = self._build_url(MercadoPagoController._url_checkout_return)
        with patch(
                'odoo.addons.payment_mercado_pago.controllers.main.MercadoPagoController'
                '.verify_notification',
                return_values=True,
        ):
            self._make_http_post_request(url, data=mp_data)
        self.assertEqual(tx.state, 'pending')

        # now confirm the transaction from the webhook
        url = self._build_url(MercadoPagoController._url_webhook)
        mp_data['status'] = 'approved'

        def dummy_request(endpoint, method, data=None):
            return mp_data

        with patch(
                'odoo.addons.payment_mercado_pago.controllers.main.MercadoPagoController'
                '.verify_notification',
                return_values=True,
        ), patch(
                    'odoo.addons.payment_mercado_pago.models.payment_acquirer.PaymentAcquirer'
                    '._mercado_pago_make_request',
                    dummy_request
        ):
            self._make_json_request(url, data=MercadoPagoCommon.WEBHOOK_DATA)

        self.assertEqual(tx.state, 'done')

    def test_mercado_pago_neutralize(self):
        self.env['payment.acquirer']._neutralize()

        self.assertEqual(self.acquirer.mercado_pago_access_token, False)
