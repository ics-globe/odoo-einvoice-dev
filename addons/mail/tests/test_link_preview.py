# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from functools import partial

import base64
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged
from unittest.mock import patch
import requests

mail_channel_new_test_user = partial(mail_new_test_user, context={'mail_channel_nosubscribe': False})

def _patched_get_html(*args, **kwargs):
    response = requests.Response()
    response.status_code = 200
    response._content = b"""
    <html>
    <head>
    <meta property="og:title" content="Test title">
    <meta property="og:description" content="Test description">
    </head>
    </html>
    """
    response.headers["Content-Type"] = 'text/html'
    return response

def _patched_get_html_with_image(*args, **kwargs):
    response = requests.Response()
    response.status_code = 200
    if (args[0] == 'get_image_content'):
        return _patched_get_image(args, kwargs)
    else:
        response._content = b"""
        <html>
        <head>
        <meta property="og:title" content="Test title">
        <meta property="og:description" content="Test description">
        <meta property="og:image" content="get_image_content">
        </head>
        </html>
        """
        response.headers["Content-Type"] = 'text/html'
    return response

def _patched_get_image(*args, **kwargs):
    response = requests.Response()
    response.status_code = 200
    response._content = base64.b64decode(b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC')
    response.headers['Content-Type'] = 'image/png'
    return response

@tagged('LinkPreview')
class TestLinkPreview(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLinkPreview, cls).setUpClass()

        cls.user_1 = mail_channel_new_test_user(
            cls.env, login='user_1',
            name='User 1',
            groups='base.group_user')

        cls.public_channel = cls.env['mail.channel'].create({
            'name': 'Public channel of user 1',
            'public': 'public',
            'channel_type': 'channel',
        })
        cls.public_channel.channel_last_seen_partner_ids.unlink()

    def test_01_link_preview_throttle(self):
        with patch.object(requests, 'get', _patched_get_html):
            channel_partner = self.env['mail.channel.partner'].with_user(self.user_1).search([('partner_id', '=', self.user_1.partner_id.id)])[0]
            for _ in range(105):
                self.env['ir.attachment']._create_link_preview('https://tenor.com', channel_partner)
        link_previews = self.env['ir.attachment'].search_count([('mimetype', '=', 'application/o-linkpreview')])
        self.assertEqual(link_previews, 100)

    def test_02_link_preview_create(self):
        with patch.object(requests, 'get', _patched_get_html):
            channel_partner = self.env['mail.channel.partner'].with_user(self.user_1).search([('partner_id', '=', self.user_1.partner_id.id)])[0]
            link_preview = self.env['ir.attachment']._create_link_preview('https://tenor.com', channel_partner)
        self.assertEqual(link_preview['description'], 'Test description')
        self.assertEqual(link_preview['name'], 'Test title')
        self.assertEqual(link_preview['filename'], 'Test title')

    def test_03_link_preview_mimetype(self):
        with patch.object(requests, 'get', _patched_get_html):
            channel_partner = self.env['mail.channel.partner'].with_user(self.user_1).search([('partner_id', '=', self.user_1.partner_id.id)])[0]
            link_preview = self.env['ir.attachment']._create_link_preview('https://tenor.com', channel_partner)
        self.assertEqual(link_preview['mimetype'], 'application/o-linkpreview')

        with patch.object(requests, 'get', _patched_get_html_with_image):
            channel_partner = self.env['mail.channel.partner'].with_user(self.user_1).search([('partner_id', '=', self.user_1.partner_id.id)])[0]
            link_preview = self.env['ir.attachment']._create_link_preview('https://tenor.com', channel_partner)
        self.assertEqual(link_preview['mimetype'], 'application/o-linkpreview-with-thumbnail')

        with patch.object(requests, 'get', _patched_get_image):
            channel_partner = self.env['mail.channel.partner'].with_user(self.user_1).search([('partner_id', '=', self.user_1.partner_id.id)])[0]
            link_preview = self.env['ir.attachment']._create_link_preview('https://tenor.com', channel_partner)
        self.assertEqual(link_preview['mimetype'], 'image/o-linkpreview-image')
