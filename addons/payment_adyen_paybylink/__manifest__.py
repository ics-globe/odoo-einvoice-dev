# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Adyen Payment Acquirer PayByLink Patch",
    'category': 'Accounting/Payment',
    'summary': 'Payment Acquirer: Adyen PayByLink Patch',
    'version': '1.0',
    'description': """
This module migrates the Adyen implementation from Hosted Payment Pages API to the PayByLink API.
    """,
    'depends': ['payment_adyen'],
    'data': [
        'views/payment_views.xml',
        'views/payment_adyen_templates.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3'
}
