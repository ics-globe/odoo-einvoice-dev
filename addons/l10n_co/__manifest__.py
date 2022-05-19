# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) David Arnold (XOE Solutions).
# Author        David Arnold (XOE Solutions), dar@xoe.solutions
# Co-Authors    Juan Pablo Aries (devCO), jpa@devco.co
#               Hector Ivan Valencia Muñoz (TIX SAS)
#               Nhomar Hernandez (Vauxoo)
#               Humberto Ochoa (Vauxoo)

{
    'name': 'Colombia - Accounting',
    'version': '0.8',
    'category': 'Accounting/Localizations/Account Charts',
    'description': 'Colombian Accounting and Tax Preconfiguration',
    'author': 'David Arnold (XOE Solutions)',
    'website': 'https://www.odoo.com/colombia',
    'depends': [
        'account',
        'account_debit_note',
        'l10n_latam_base',
    ],
    'data': [
        # Chart of Accounts
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/account.group.template.csv',

        # Taxes
        'data/account.tax.group.csv',
        'data/account_tax_template.xml',
        'data/l10n_latam.identification.type.csv',

        'data/account_chart_post_data.xml',
        'data/account_chart_template_try_loading.xml',

        # Views
        'views/menuitem_data.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}
