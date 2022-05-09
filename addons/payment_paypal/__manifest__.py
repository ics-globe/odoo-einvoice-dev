# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Paypal Payment Provider',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 365,
    'summary': 'Payment Provider: Paypal Implementation',
    'description': """Paypal Payment Provider""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_paypal_templates.xml',
        'data/payment_provider_data.xml',
        'data/payment_paypal_email_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
