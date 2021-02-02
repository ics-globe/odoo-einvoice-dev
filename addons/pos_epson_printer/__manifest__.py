# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'pos_epson_printer',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Epson ePOS Printers in PoS',
    'description': """

Use Epson ePOS Printers without the IoT Box in the Point of Sale
""",
    'depends': ['point_of_sale'],
    'data': [
        
        'views/pos_config_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'assets': [
            # inside .
            'pos_epson_printer/static/src/js/pos_epson_printer.js',
            # inside .
            'pos_epson_printer/static/src/js/printers.js',
            # inside .
            'pos_epson_printer/static/lib/epos-2.12.0.js',
        ],
    }
}
