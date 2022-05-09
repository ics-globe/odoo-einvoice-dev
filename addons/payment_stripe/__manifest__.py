# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Stripe Payment Provider',
    'version': '2.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 380,
    'summary': 'Payment Provider: Stripe Implementation',
    'description': """Stripe Payment Provider""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_stripe/static/src/js/payment_form.js',
        ],
    },
    'license': 'LGPL-3',
}
