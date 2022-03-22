# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Razorpay Payment Acquirer',
    'version': '1.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 375,
    'summary': 'Payment Acquirer: Razorpay Implementation',
        'description': """
Razorpay Payment Acquirer for India.

Razorpay payment gateway supports only INR currency.
""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_razorpay_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
