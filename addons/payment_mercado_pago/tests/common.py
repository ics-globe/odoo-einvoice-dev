# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.payment.tests.common import PaymentCommon


class MercadoPagoCommon(PaymentCommon):

    MP_PAYMENT_ID = '1234567890'

    NOTIFICATION_DATA = {
            'collection_id': '1247406693',
            'collection_status': 'approved',
            'merchant_account_id': 'null',
            'merchant_order_id': '4490339123',
            'payment_id': MP_PAYMENT_ID,
            'payment_type': 'credit_card',
            'preference_id': 'dummy_preference',
            'processing_mode': 'aggregator',
            'site_id': 'MLM',
    }

    WEBHOOK_DATA = {
        'action': 'payment.updated',
        'api_version': 'v1',
        'data': {'id': MP_PAYMENT_ID},
        'date_created': '2022-04-07T10:46:16Z',
        'id': 101302302589,
        'live_mode': False,
        'type': 'payment',
        'user_id': '1086311584'
    }

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.mercado_pago = cls._prepare_acquirer('mercado_pago', update_values={
            'mercado_pago_access_token':
                'TEST-4850554046279901-031018-8112ffc69bee4b304a492d2b617ff96e-1086311584',
        })

        cls.acquirer = cls.mercado_pago
