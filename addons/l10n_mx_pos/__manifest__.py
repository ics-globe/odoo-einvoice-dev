# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Mexico - Point of Sale',
    'author': 'Odoo PS',
    'category': 'Accounting/Localizations/Point of Sale',
    'description': """
United Arab Emirates POS Localization
=======================================================
    """,
    'depends': [
        'l10n_mx',
        'point_of_sale',
        ],
    'data': [
        'data/product_data.xml',
        'views/pos_config_view.xml',
        'views/pos_order_view.xml',
        ],
    'qweb': ['static/src/xml/Screens/ReceiptScreen/OrderReceipt.xml'],
    'auto_install': True,
    'license': 'LGPL-3',
}
