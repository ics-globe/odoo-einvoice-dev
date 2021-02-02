# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Notes',
    'version': '1.0',
    'category': 'Productivity/Notes',
    'description': "",
    'website': 'https://www.odoo.com/page/notes',
    'summary': 'Organize your work with memos',
    'sequence': 260,
    'depends': [
        'mail',
    ],
    'data': [
        'security/note_security.xml',
        'security/ir.model.access.csv',
        'data/mail_activity_data.xml',
        'data/note_data.xml',
        'data/res_users_data.xml',
        'views/note_views.xml',
        
    ],
    'demo': [
        'data/note_demo.xml',
    ],
    'qweb': [
        'static/src/xml/systray.xml',
    ],
    'test': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'assets_backend': [
            # after //link[last()]
            'note/static/src/scss/note.scss',
            # after //script[last()]
            'note/static/src/js/systray_activity_menu.js',
        ],
        'qunit_suite': [
            # inside .
            'note/static/tests/systray_activity_menu_tests.js',
        ],
    }
}
