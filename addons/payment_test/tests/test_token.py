# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from .common import PaymentTestCommon
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_test.controllers.main import PaymentTestController
from odoo.addons.payment.tests.http_common import PaymentHttpCommon

@tagged('-at_install', 'post_install')
class TestToken(PaymentTestCommon, PaymentHttpCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.done_token = cls.env['payment.token'].create({
            'acquirer_id': cls.acquirer.id,
            'name': payment_utils.build_token_name(payment_details_short='4756'),
            'partner_id': cls.partner.id,
            'acquirer_ref': 'fake acquirer reference',
            'verified': True,
            'test_state': 'done',
        })

        cls.pending_token = cls.env['payment.token'].create({
            'acquirer_id': cls.acquirer.id,
            'name': payment_utils.build_token_name(payment_details_short='4756'),
            'partner_id': cls.partner.id,
            'acquirer_ref': 'fake acquirer reference',
            'verified': True,
            'test_state': 'pending',
        })

        cls.error_token = cls.env['payment.token'].create({
            'acquirer_id': cls.acquirer.id,
            'name': payment_utils.build_token_name(payment_details_short='4756'),
            'partner_id': cls.partner.id,
            'acquirer_ref': 'fake acquirer reference',
            'verified': True,
            'test_state': 'error',
        })

        cls.cancel_token = cls.env['payment.token'].create({
            'acquirer_id': cls.acquirer.id,
            'name': payment_utils.build_token_name(payment_details_short='4756'),
            'partner_id': cls.partner.id,
            'acquirer_ref': 'fake acquirer reference',
            'verified': True,
            'test_state': 'cancel',
        })

    #=== MANUAL CAPTURE AND TOKEN ===#

    def test_token_transaction_state_with_manual_capture(self):
        self.acquirer.capture_manually = True

        tx = self.create_transaction(flow='direct')
        tx.token_id = self.done_token.id
        tx._send_payment_request()

        self.assertEqual(
            tx.state,
            'authorized',
            msg="Payment through token: The transaction state should be 'authorized' when manual "
                "capture is enabled.",
        )

        tx._send_capture_request()
        self.assertEqual(
            tx.state,
            'done',
            msg="Payment through token: The transaction state should be 'done' when a capture "
                "request is sent over an authorized transaction",
        )

    def test_token_transaction_state_void_with_manual_capture(self):
        self.acquirer.capture_manually = True

        tx = self.create_transaction(flow='direct')
        tx.token_id = self.done_token.id
        tx._send_payment_request()
        tx._send_void_request()
        self.assertEqual(
            tx.state,
            'cancel',
            msg="Payment through token: The transaction state should be 'cancel' when a void "
                "request is sent over an authorized transaction",
        )

    #=== TOKEN ===#

    def test_token_controller_payment_test(self):
        tx = self.create_transaction(flow='direct')
        tx.token_id = self.done_token.id
        tx._send_payment_request()
        self.assertEqual(
            tx.state,
            'done',
            msg="Payment through token: The transaction state should be 'done' when manual capture "
                "isn't enabled.",
        )

    def test_token_controller_cancel_payment_test(self):
        tx = self.create_transaction(flow='direct')
        tx.token_id = self.cancel_token.id
        tx._send_payment_request()
        self.assertEqual(
            tx.state,
            'cancel',
            msg="Payment through token: The transaction state should be 'cancel' when the state "
                "recorded in the token is 'cancel'",
        )

    def test_token_controller_pending_payment_test(self):
        tx = self.create_transaction(flow='direct')
        tx.token_id = self.pending_token.id
        tx._send_payment_request()
        self.assertEqual(
            tx.state,
            'pending',
            msg="Payment through token: The transaction state should be 'pending' when the state "
                "recorded in the token is 'pending'",
        )

    def test_token_controller_error_payment_test(self):
        tx = self.create_transaction(flow='direct')
        tx.token_id = self.error_token.id
        tx._send_payment_request()
        self.assertEqual(
            tx.state,
            'error',
            msg="Payment through token: The transaction state should be 'error' when the state "
                "recorded in the token is 'error'",
        )

    def test_controller_tokenize(self):
        tx = self.create_transaction(flow='direct', tokenize=True)

        url = self._build_url(PaymentTestController._simulation_url)
        self._make_json_rpc_request(url, data=self.done_data)

        self.assertEqual(
            tx.token_id.name,
            self.done_token.name,
            msg="The token name is different.",
        )
        self.assertEqual(
            tx.token_id.provider,
            self.done_token.provider,
            msg="The token provider is different.",
        )
        self.assertEqual(
            tx.token_id.acquirer_id,
            self.done_token.acquirer_id,
            msg="The token acquirer_id is different.",
        )
        self.assertEqual(
            tx.token_id.partner_id,
            self.done_token.partner_id,
            msg="The token partner_id is different.",
        )
        self.assertEqual(
            tx.token_id.acquirer_ref,
            self.done_token.acquirer_ref,
            msg="The token acquirer_ref is different.",
        )
        self.assertEqual(
            tx.token_id.test_state,
            self.done_token.test_state,
            msg="The token state is different.",
        )

    def test_controller_tokenize_state_error(self):
        tx = self.create_transaction(flow='direct', tokenize=True)

        url = self._build_url(PaymentTestController._simulation_url)
        self._make_json_rpc_request(url, data=self.error_data)

        self.assertEqual(
            tx.token_id.test_state,
            'error',
            msg="The token state should be 'error' when a payment is made from the portal "
                "and status passed to the controller is 'error'.",
        )

    def test_controller_tokenize_state_cancel(self):
        tx = self.create_transaction(flow='direct', tokenize=True)

        url = self._build_url(PaymentTestController._simulation_url)
        self._make_json_rpc_request(url, data=self.cancel_data)

        self.assertEqual(
            tx.token_id.test_state,
            'cancel',
            msg="The token state should be 'cancel' when a payment is made from the portal "
                "and status passed to the controller is 'cancel'.",
        )

    def test_controller_tokenize_state_pending(self):
        tx = self.create_transaction(flow='direct', tokenize=True)

        url = self._build_url(PaymentTestController._simulation_url)
        self._make_json_rpc_request(url, data=self.pending_data)

        self.assertEqual(
            tx.token_id.test_state,
            'pending',
            msg="The token state should be 'pending' when a payment is made from the portal "
                "and status passed to the controller is 'pending'.",
        )
