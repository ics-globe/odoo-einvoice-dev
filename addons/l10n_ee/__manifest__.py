{
    'name': 'Estonia - Accounting',
    'version': '1.0.0',
    'category': 'Accounting/Localizations/Account Charts',
    'license': 'LGPL-3',
    'depends':  [
        "account",
        #"l10n_multilang",
    ],
    'description': """
This is the module to manage the accounting chart for Estonia in Odoo.
========================================================================
""",
    'depends': [
        'account',
    ],
    'data': [
        # chart of Accounts
        'data/l10n_ee_chart_template_data.xml',
        # 'data/account_account_tag_data.xml',
        'data/account.account.template.csv',
        'data/account.group.template.csv',

        # Taxes
        'data/account_tax_group_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_fiscal_position_template_data.xml',
        'data/account_account_template_post_data.xml',

        'data/account_chart_post_data.xml',
        'data/account_chart_template_try_loading.xml',

        # Views and others
        'views/l10n_ee_views.xml',

    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    #'post_init_hook': '_l10n_ee_post_init_hook',
}