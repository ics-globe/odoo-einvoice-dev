# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Resources',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 145,
    'summary': 'Base resources',
    'depends': ['base'],
    'data': [
        'security/res_security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
