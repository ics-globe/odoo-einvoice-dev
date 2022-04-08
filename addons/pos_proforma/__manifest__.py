# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Point of sale Proforma order",
    'summary': "Allow the use of proforma order",
    'description': """Integrate proforma orders in the point of sale.""",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['point_of_sale'],
    'auto_install': False,
    'data': [
        'security/ir.model.access.csv',
        'views/proforma_views.xml',
    ],
    'license': 'LGPL-3',
}
