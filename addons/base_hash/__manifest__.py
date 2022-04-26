# -*- coding: utf-8 -*-
{
    'name': 'Hash',
    'version': '1.0',
    'category': 'Hidden/Tools',
    'description': """
This module allows Odoo models to have an inalterable hash. The records will be
hashed in a linked chain as to provide inalterability. One can easily reimplement
some methods to get this feature working for a specific model. This is specially
useful to verify the integrity of the records and be sure that after the hash is
computed, we cannot modify important fields that would break the integrity of the 
hashing chain.
""",
    'depends': ['base'],
    'data': [
        'report/hash_integrity.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
