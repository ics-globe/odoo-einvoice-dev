# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest
from datetime import datetime, timedelta
from os import getenv
from os.path import join as opj
from unittest.mock import patch
from urllib.parse import urlparse
from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tools import config, file_open, file_path
from odoo.tools.osutil import is_host_up

from .test_common import TestHttpBase


WEB_SERVER_URL = urlparse(getenv('ODOO_WEB_SERVER_URL', 'http://odoo.localhost:80'))
SKIP_WEB_SERVER_TESTS = not is_host_up(WEB_SERVER_URL.hostname, WEB_SERVER_URL.port)


@tagged('post_install', '-at_install')
class TestHttpStatic(TestHttpBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.classPatch(config, 'options', {**config.options, 'x_sendfile': False})

    def test_static0_png_image(self):
        with self.subTest(x_sendfile=False):
            res = self.nodb_url_open("/test_http/static/src/img/gizeh.png")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get('Content-Length'), '814')
            self.assertEqual(res.headers.get('Content-Type'), 'image/png')
            with file_open('test_http/static/src/img/gizeh.png', 'rb') as file:
                self.assertEqual(res.content, file.read())

        with self.subTest(x_sendfile=True), \
             patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            res = self.nodb_url_open("/test_http/static/src/img/gizeh.png")
            res.raise_for_status()
            self.assertEqual(res.content, b'', "The web server should send the file instead of Odoo.")
            self.assertEqual(
                res.headers.get('X-Accel-Redirect'),
                '/web/filesystem' + file_path('test_http/static/src/img/gizeh.png')
            )

    def test_static1_svg_image(self):
        uri = '/test_http/static/src/img/gizeh.svg'

        with self.subTest(x_sendfile=False):
            res = self.nodb_url_open(uri)
            res.raise_for_status()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get('Content-Length'), '1529')
            self.assertEqual(res.headers.get('Content-Type'), 'image/svg+xml; charset=utf-8')
            self.assertEqual(res.headers.get('Content-Disposition'), "inline; filename=gizeh.svg")
            with file_open('test_http/static/src/img/gizeh.svg', 'rb') as file:
                self.assertEqual(res.content, file.read())

        with self.subTest(x_sendfile=True), \
             patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            res = self.nodb_url_open(uri)
            res.raise_for_status()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get('Content-Length'), '1529')
            self.assertEqual(res.headers.get('Content-Type'), 'image/svg+xml; charset=utf-8')
            self.assertEqual(res.headers.get('Content-Disposition'), "inline; filename=gizeh.svg")
            self.assertEqual(res.headers.get('X-Sendfile'), file_path(uri[1:]))
            self.assertEqual(res.headers.get('X-Accel-Redirect'), '/web/filesystem' + file_path(uri[1:]))
            self.assertFalse(res.content)


    def test_static2_not_found(self):
        res = self.nodb_url_open("/test_http/static/i-dont-exist")
        self.assertEqual(res.status_code, 404)

    def test_static3_attachment_fallback(self):
        attachment = self.env.ref('test_http.lipsum')
        attachment_path = opj(config.filestore(self.env.cr.dbname), attachment.store_fname)

        with self.subTest(x_sendfile=False):
            res = self.db_url_open(attachment['url'])
            res.raise_for_status()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get('Content-Length'), '56')
            self.assertEqual(res.headers.get('Content-Type'), 'text/plain; charset=utf-8')
            self.assertEqual(res.headers.get('Content-Disposition'), "inline; filename=lipsum.txt")
            self.assertEqual(res.content, attachment.raw)

        with self.subTest(x_sendfile=True), \
             patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            res = self.db_url_open(attachment['url'])
            res.raise_for_status()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get('Content-Length'), '56')
            self.assertEqual(res.headers.get('Content-Type'), 'text/plain; charset=utf-8')
            self.assertEqual(res.headers.get('Content-Disposition'), "inline; filename=lipsum.txt")
            self.assertEqual(res.headers.get('X-Sendfile'), attachment_path)
            self.assertEqual(res.headers.get('X-Accel-Redirect'), '/web/filesystem' + attachment_path)
            self.assertFalse(res.content)

    def test_static4_web_content(self):
        xmlid = 'test_http.lipsum'
        attachment = self.env.ref(xmlid)
        attachment_path = opj(config.filestore(self.env.cr.dbname), attachment.store_fname)

        with self.subTest(x_sendfile=False):
            res = self.db_url_open(f'/web/content/{xmlid}')
            res.raise_for_status()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get('Content-Length'), '56')
            self.assertEqual(res.headers.get('Content-Type'), 'text/plain; charset=utf-8')
            self.assertEqual(res.headers.get('Content-Disposition'), "inline; filename=lipsum.txt")
            self.assertEqual(res.content, attachment.raw)

        with self.subTest(x_sendfile=True), \
             patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            res = self.db_url_open(f'/web/content/{xmlid}')
            res.raise_for_status()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get('Content-Length'), '56')
            self.assertEqual(res.headers.get('Content-Type'), 'text/plain; charset=utf-8')
            self.assertEqual(res.headers.get('Content-Disposition'), "inline; filename=lipsum.txt")
            self.assertEqual(res.headers.get('X-Sendfile'), attachment_path)
            self.assertEqual(res.headers.get('X-Accel-Redirect'), '/web/filesystem' + attachment_path)
            self.assertFalse(res.content)

    def test_static5_web_image(self):
        xmlid = 'test_http.one_pixel_png'
        attachment = self.env.ref(xmlid)
        attachment_path = opj(config.filestore(self.env.cr.dbname), attachment.store_fname)

        with self.subTest(x_sendfile=False):
            res = self.db_url_open(f'/web/image/{xmlid}')
            res.raise_for_status()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get('Content-Length'), '70')
            self.assertEqual(res.headers.get('Content-Type'), 'image/png')
            self.assertEqual(res.headers.get('Content-Security-Policy'), "default-src 'none'")
            self.assertEqual(res.headers.get('Content-Disposition'), "inline; filename=one_pixel.png")
            self.assertEqual(res.content, attachment.raw, res.content)

        with self.subTest(x_sendfile=True), \
             patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            res = self.db_url_open(f'/web/content/{xmlid}')
            res.raise_for_status()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get('Content-Length'), '70')
            self.assertEqual(res.headers.get('Content-Type'), 'image/png')
            self.assertEqual(res.headers.get('Content-Security-Policy'), "default-src 'none'")
            self.assertEqual(res.headers.get('Content-Disposition'), "inline; filename=one_pixel.png")
            self.assertEqual(res.headers.get('X-Sendfile'), attachment_path)
            self.assertEqual(res.headers.get('X-Accel-Redirect'), '/web/filesystem' + attachment_path)
            self.assertFalse(res.content)

    @freeze_time(datetime.utcnow())
    def test_static6_cache(self, domain=''):

        # Wed, 21 Oct 2015 07:28:00 GMT
        # The timezone should be %Z (instead of 'GMT' hardcoded) but
        # somehow strftime doesn't set it.
        http_date_format = '%a, %d %b %Y %H:%M:%S GMT'
        one_week_away = (datetime.utcnow() + timedelta(weeks=1)).strftime(http_date_format)

        res1 = self.nodb_url_open(f"{domain}/test_http/static/src/img/gizeh.png")
        res1.raise_for_status()
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.headers.get('Cache-Control'), 'public, max-age=604800')  # one week
        self.assertEqual(res1.headers.get('Expires'), one_week_away)
        self.assertIn('ETag', res1.headers)

        res2 = self.nodb_url_open(f"{domain}/test_http/static/src/img/gizeh.png", headers={
            "If-None-Match": res1.headers['ETag']
        })
        res2.raise_for_status()
        self.assertEqual(res2.status_code, 304, "We should not download the file again.")

    @unittest.skipIf(SKIP_WEB_SERVER_TESTS, 'There is no web server in front of Odoo.')
    def test_static7_web_server_cache(self):
        with patch.object(config, 'options', {**config.options, 'x_sendfile': True}):
            self.test_static6_cache(domain=WEB_SERVER_URL.geturl())

    def test_static8_attachment_url_redirect(self):
        xmlid = 'test_http.rickroll'
        attachment = self.env.ref(xmlid)

        res = self.db_url_open(f'/web/content/{attachment.id}')
        res.raise_for_status()
        self.assertEqual(res.status_code, 301)
        self.assertEqual(res.headers.get('Location'), attachment.url)

    def test_static9_attachment_url_path(self):
        xmlid = 'test_http.gizeh_png'
        attachment = self.env.ref(xmlid)

        res = self.db_url_open(f'/web/content/{attachment.id}')
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Content-Length'), '814')
        self.assertEqual(res.headers.get('Content-Type'), 'image/png')
        with file_open('test_http/static/src/img/gizeh.png', 'rb') as file:
            self.assertEqual(res.content, file.read())
