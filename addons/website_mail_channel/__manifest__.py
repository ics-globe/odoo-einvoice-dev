# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Website Mail Channels',
    'category': 'Website/Website',
    'summary': 'Allow visitors to join public mail channels',
    'description': """
Visitors can join public mail channels managed in the Discuss app in order to get regular updates or reach out with your community.
    """,
    'depends': ['website_mail'],
    'data': [
        'data/mail_template_data.xml',
        
        'views/snippets/s_channel.xml',
        'views/snippets/snippets.xml',
        'views/website_mail_channel_templates.xml',
    ],
    'assets': {
        'assets_snippet_s_channel_js_000': [
            # after //script[last()]
            'website_mail_channel/static/src/snippets/s_channel/000.js',
        ],
        'assets_frontend': [
            # after //link[last()]
            'website_mail_channel/static/src/css/website_mail_channel.css',
            # after //script[last()]
            'website_mail_channel/static/src/js/website_mail_channel.js',
        ],
        'assets_wysiwyg': [
            # after //script[last()]
            'website_mail_channel/static/src/snippets/s_channel/options.js',
        ],
    }
}
