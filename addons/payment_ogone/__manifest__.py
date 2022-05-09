# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ogone Payment Provider',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 360,
    'summary': 'Payment Provider: Ogone Implementation',
    'description': """Ogone Payment Provider""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_ogone_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
