# -*- coding: utf-8 -*-

{
    'name': 'Payment - Account',
    'category': 'Accounting/Accounting',
    'summary': 'Account and Payment Link and Portal',
    'version': '1.0',
    'description': """Link Account and Payment and add Portal Payment

Provide tools for account-related payment as well as portal options to
enable payment.

 * UPDATE ME
""",
    'depends': ['account', 'payment'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',

        'views/account_payment_menus.xml',

        'views/account_portal_templates.xml',
        'views/payment_templates.xml',

        'views/account_invoice_views.xml',
        'views/account_journal_views.xml',
        'views/account_payment_views.xml',
        'views/payment_transaction_views.xml',

        'wizards/account_payment_register_views.xml',
        'wizards/payment_link_wizard_views.xml',
        # TODO onboarding (acc_payment or payment ???)
        # 'wizards/payment_acquirer_onboarding_templates.xml',
    ],
    'installable': True,
    'auto_install': ['account'],
    'license': 'LGPL-3',
}
