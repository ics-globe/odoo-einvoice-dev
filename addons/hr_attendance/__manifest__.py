# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Attendances',
    'version': '2.0',
    'category': 'Human Resources/Attendances',
    'sequence': 240,
    'summary': 'Track employee attendance',
    'description': """
This module aims to manage employee's attendances.
==================================================

Keeps account of the attendances of the employees on the basis of the
actions(Check in/Check out) performed by them.
       """,
    'website': 'https://www.odoo.com/page/employees',
    'depends': ['hr', 'barcodes'],
    'data': [
        'security/hr_attendance_security.xml',
        'security/ir.model.access.csv',
        
        'views/hr_attendance_view.xml',
        'views/hr_department_view.xml',
        'views/hr_employee_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'data/hr_attendance_demo.xml'
    ],
    'installable': True,
    'auto_install': False,
    'qweb': [
        "static/src/xml/attendance.xml",
    ],
    'application': True,
    'assets': {
        'assets_backend': [
            # inside .
            'hr_attendance/static/src/js/employee_kanban_view_handler.js',
            # inside .
            'hr_attendance/static/src/js/greeting_message.js',
            # inside .
            'hr_attendance/static/src/js/kiosk_mode.js',
            # inside .
            'hr_attendance/static/src/js/kiosk_confirm.js',
            # inside .
            'hr_attendance/static/src/js/my_attendances.js',
            # inside .
            'hr_attendance/static/src/js/time_widget.js',
            # inside .
            'hr_attendance/static/src/scss/hr_attendance.scss',
        ],
        'qunit_suite': [
            # after //script[contains(@src, '/web/static/tests/views/kanban_tests.js')]
            'hr_attendance/static/tests/hr_attendance_tests.js',
        ],
    }
}
