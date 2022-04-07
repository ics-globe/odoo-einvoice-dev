# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website - Payment Stripe',
    'version': '1.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 365,
    'summary': 'Website - Payment Stripe',
    'description': """""",
    'depends': ['website_payment', 'payment_stripe'],
    'data': [
        'views/payment_acquirer.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
