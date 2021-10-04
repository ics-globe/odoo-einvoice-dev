# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from .common import PaymentTestCommon
from odoo.addons.payment_test.controllers.main import PaymentTestController
from odoo.addons.payment.tests.http_common import PaymentHttpCommon

@tagged('-at_install', 'post_install')
class TestAcquirer(PaymentTestCommon, PaymentHttpCommon):

    #=== DIRECT ===#

    def test_controller_payment_test(self):
        tx = self.create_transaction(flow='direct')

        url = self._build_url(PaymentTestController._simulation_url)
        self._make_json_rpc_request(url, data=self.done_data)

        self.assertEqual(
            tx.state,
            'done',
            msg="The transaction state should be 'done' when a payment is made from the portal.",
        )

    def test_controller_cancel_payment_test(self):
        tx = self.create_transaction(flow='direct')

        url = self._build_url(PaymentTestController._simulation_url)
        self._make_json_rpc_request(url, data=self.cancel_data)

        self.assertEqual(
            tx.state,
            'cancel',
            msg="The transaction state should be 'cancel' when a payment is made from the portal "
                "and status passed to the controller is 'cancel'.",
        )

    def test_controller_pending_payment_test(self):
        tx = self.create_transaction(flow='direct')

        url = self._build_url(PaymentTestController._simulation_url)
        self._make_json_rpc_request(url, data=self.pending_data)

        self.assertEqual(
            tx.state,
            'pending',
            msg="The transaction state should be 'pending' when a payment is made from the portal "
                "and status passed to the controller is 'pending'.",
        )

    def test_controller_error_payment_test(self):
        tx = self.create_transaction(flow='direct')

        url = self._build_url(PaymentTestController._simulation_url)
        self._make_json_rpc_request(url, data=self.error_data)

        self.assertEqual(
            tx.state,
            'error',
            msg="The transaction state should be 'error' when a payment is made from the portal "
                "and status passed to the controller is 'error'.",
        )

    #=== FEES ===#

    def test_fees_payment_test(self):
        # update acquirer: compute fees
        self.acquirer.write({
            'fees_active': True,
            'fees_dom_fixed': 1.0,
            'fees_dom_var': 0.35,
            'fees_int_fixed': 1.5,
            'fees_int_var': 0.50,
        })

        transaction_fees = self.currency.round(
            self.acquirer._compute_fees(
                self.amount,
                self.currency,
                self.partner.country_id,
            )
        )
        self.assertEqual(transaction_fees, 7.09)
        total_fee = self.currency.round(self.amount + transaction_fees)
        self.assertEqual(total_fee, 1118.2)

        tx = self.create_transaction(flow='direct')
        self.assertEqual(tx.fees, 7.09)

    #=== REFUND ===#

    def test_full_refund_payment_test(self):
        tx = self.create_transaction(flow='direct', state='done')
        tx._reconcile_after_done()  # Create the payment

        refund_tx = tx._send_refund_request()
        refund_tx._reconcile_after_done()  # Create the payment

        self.assertEqual(tx.payment_id.refunds_count, 1, msg="")
        self.assertEqual(tx.amount, -refund_tx.amount, msg="")


    def test_partial_refund_payment_test(self):
        tx = self.create_transaction(flow='direct', state='done')
        tx._reconcile_after_done()  # Create the payment

        refund_tx = tx._send_refund_request(500)
        refund_tx._reconcile_after_done()  # Create the payment

        self.assertEqual(tx.payment_id.refunds_count, 1, msg="")
        self.assertEqual(refund_tx.amount, -500, msg="")

    def test_multiple_partial_refund_payment_test(self):
        tx = self.create_transaction(flow='direct', state='done')
        tx._reconcile_after_done()  # Create the payment

        refund_tx = tx._send_refund_request(500)
        refund_tx._reconcile_after_done()  # Create the payment

        second_refund_tx = tx._send_refund_request(500)
        second_refund_tx._reconcile_after_done()  # Create the payment

        self.assertEqual(tx.payment_id.refunds_count, 2, msg="")
        self.assertEqual(refund_tx.amount, -500, msg="")
        self.assertEqual(second_refund_tx.amount, -500, msg="")

    def test_refund_no_transaction_payment_test(self):
        tx = self.create_transaction(flow='direct', state='done')
        tx._reconcile_after_done()  # Create the payment

        refund_tx = tx._send_refund_request(500, False)
        self.assertEqual(len(refund_tx), 0, msg="")
        self.assertEqual(tx.payment_id.refunds_count, 0, msg="")

    #=== MANUAL CAPTURE ===#

    def test_transaction_state_with_manual_capture(self):
        self.acquirer.capture_manually = True

        tx = self.create_transaction(flow='redirect')

        url = self._build_url(PaymentTestController._simulation_url)
        self._make_json_rpc_request(url, data=self.done_data)

        self.assertEqual(
            tx.state,
            'authorized',
            msg="The transaction state should be 'authorized' when manual capture is enabled.",
        )

        tx._send_capture_request()
        self.assertEqual(
            tx.state,
            'done',
            msg="The transaction state should be 'done' when a capture request is sent over an "
                "authorized transaction",
        )

    def test_transaction_state_void_with_manual_capture(self):
        self.acquirer.capture_manually = True

        tx = self.create_transaction(flow='direct')

        url = self._build_url(PaymentTestController._simulation_url)
        self._make_json_rpc_request(url, data=self.done_data)

        tx._send_void_request()
        self.assertEqual(
            tx.state,
            'cancel',
            msg="The transaction state should be 'cancel' when a void request is sent over an "
                "authorized transaction",
        )

    def test_state_pending_manual_capture(self):
        self.acquirer.capture_manually = True

        tx = self.create_transaction(flow='direct')

        url = self._build_url(PaymentTestController._simulation_url)
        self._make_json_rpc_request(url, data=self.pending_data)

        self.assertEqual(
            tx.state,
            'pending',
            msg="The transaction state should be 'pending' when manual capture is enabled but "
                "status received from the controller is 'pending'.",
        )

    def test_state_cancel_manual_capture(self):
        self.acquirer.capture_manually = True

        tx = self.create_transaction(flow='direct')

        url = self._build_url(PaymentTestController._simulation_url)
        self._make_json_rpc_request(url, data=self.cancel_data)

        self.assertEqual(
            tx.state,
            'cancel',
            msg="The transaction state should be 'cancel' when manual capture is enabled but "
                "status received from the controller is 'cancel'.",
        )
