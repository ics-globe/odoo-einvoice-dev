# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PayuLatam Payment Provider',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 370,
    'summary': 'Payment Provider: PayuLatam Implementation',
    'description': """Payulatam payment provider""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_payulatam_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
