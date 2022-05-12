# -*- coding: utf-8 -*-
{
    'name': "Testing the Import/Export invoices with UBL/CII",
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
    This module tests the module 'account_edi_ubl_cii', it is a separate module since dependencies to some 
    localizations were required. Name begins by 'l10n' to not overload runbot.
    """,
    'depends': [
        'l10n_generic_coa',
        'account_edi_ubl_cii',
        'l10n_fr',
        'l10n_be',
        'l10n_de',
        'l10n_nl_edi',
    ],
    'category': 'Hidden/Tests',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
