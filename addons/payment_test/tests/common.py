# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.payment.tests.common import PaymentCommon


class PaymentTestCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.acquirer = cls._prepare_acquirer(provider='test', update_values={
            'capture_manually': False, # Only activate manual capture in dedicated tests
            'fees_active': False, # Only activate fees in dedicated tests
        })

        cls.pending_data = {
            'reference': 'Test Transaction',
            'customer_input': '3746356486794756',
            'status': 'pending',
        }

        cls.done_data = {
            'reference': 'Test Transaction',
            'customer_input': '3746356486794756',
            'status': 'done',
        }

        cls.error_data = {
            'reference': 'Test Transaction',
            'customer_input': '3746356486794756',
            'status': 'error',
        }

        cls.cancel_data = {
            'reference': 'Test Transaction',
            'customer_input': '3746356486794756',
            'status': 'cancel',
        }
