# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Landed Costs With Subcontracting order',
    'version': '1.0',
    'summary': 'Advanced views to manage landed cost for subcontracting orders',
    'description': """
This module allows add some search and details in order to manage landed cost for
subcontracting orders.
    """,
    'depends': ['stock_landed_costs', 'mrp_subcontracting'],
    'category': 'Manufacturing/Manufacturing',
    'data': [
        'views/stock_landed_cost_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
