# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PayuMoney Payment Provider',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 375,
    'summary': 'Payment Provider: PayuMoney Implementation',
    'description': """
PayuMoney Payment Provider for India.

PayUmoney payment gateway supports only INR currency.
""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_payumoney_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
