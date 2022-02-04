# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mercado Pago Payment Acquirer',
    'version': '2.0',
    'category': 'Accounting/Payment Acquirers',
    'sequence': 350,
    'summary': 'Payment Acquirer: Mercado Pago Implementation',
    'description': """Mercado Pago Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_mercado_pago/static/src/js/payment_form.js',
        ],
    },
    'license': 'LGPL-3',
}
