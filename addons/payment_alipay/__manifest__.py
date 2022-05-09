# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Alipay Payment Provider',
    'category': 'Accounting/Payment Providers',
    'version': '2.0',
    'sequence': 345,
    'summary': 'Payment Provider: Alipay Implementation',
    'description': """Alipay Payment Provider""",
    'depends': ['payment'],
    'data': [
        'views/payment_alipay_templates.xml',
        'views/payment_views.xml',
        'data/payment_provider_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
