# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Discuss',
    'version': '1.0',
    'category': 'Productivity/Discuss',
    'sequence': 145,
    'summary': 'Chat and channels',
    'website': 'https://www.odoo.com/app/discuss',
    'depends': ['bus', 'res', 'web_tour'],
    'data': [
        'security/discuss_security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'discuss/static/src/js/emojis.js',
            'discuss/static/src/js/utils.js',
            'discuss/static/src/component_hooks/*/*.js',
            'discuss/static/src/components/*/*.js',
            'discuss/static/src/components/*/*.scss',
            'discuss/static/src/model/*.js',
            'discuss/static/src/models/*/*.js',
            'discuss/static/src/services/*/*.js',
            'discuss/static/src/utils/*/*.js',
            'discuss/static/src/utils/utils.js',
            'discuss/static/src/widgets/*/*.js',
            'discuss/static/src/widgets/*/*.scss',
        ],
        'web.assets_backend_prod_only': [
            'discuss/static/src/main.js',
        ],
        'web.assets_qweb': [
            'discuss/static/src/components/*/*.xml',
            'discuss/static/src/widgets/*/*.xml',
        ],
        'web.tests_assets': [
            'discuss/static/src/env/test_env.js',
            'discuss/static/src/utils/test_utils.js',
            'discuss/static/tests/helpers/mock_models.js',
            'discuss/static/tests/helpers/mock_server.js',
        ],
        'web.qunit_suite_tests': [
            'discuss/static/src/component_hooks/*/tests/*.js',
            'discuss/static/src/components/*/tests/*.js',
        ],
    },
}
