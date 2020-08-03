from collections import defaultdict
from itertools import product

from lxml import html
from werkzeug.test import Client
from werkzeug.urls import url_encode, url_parse
from werkzeug.wrappers import BaseResponse

from odoo import http
from odoo.tests import HttpCase
from odoo.tools import mute_logger


class TestMailAccess(HttpCase):
    def _cleanup(self, location):
        # we want the absolute path but not the absolute URL, strip out bullshit
        # scheme & domain, as well as fragment as Werkzeug's client doesn't
        # support those (TBF they're a client-only concern)
        return url_parse(location).replace(scheme='', netloc='', fragment='').to_url()

    def do_login(self, client, body, user):
        h = html.fromstring(body)
        f = h.find('.//form[@class="oe_login_form"]')
        fields = {
            field.get('name'): field.get('value')
            for field in f.xpath('.//input[@name] | .//button[@name]')
            if field.get('value')
        }
        fields['login'] = fields['password'] = user
        r = client.post(f.get('action'), data=fields, environ_base={
            'REMOTE_HOST': 'localhost',
            'REMOTE_ADDR': '127.0.0.1',
        })
        return r.headers['Location'], self._cleanup(r.headers['Location'])

    def do_flow(self, model, user, *, login, token):
        params = {}
        Model = self.env[model]
        if token and 'access_token' in Model._fields:
            params = {'access_token': '12345'}

        obj = Model.create(params)
        c = Client(http.root, BaseResponse)
        if login:
            self.authenticate(user, user)
            c.set_cookie('localhost', key='session_id', value=self.session.sid, httponly=True)
        else:
            self.env.cr.flush()
            self.env.cr.clear()
        location = url = '/mail/view?' + url_encode({
            'model': model,
            'res_id': obj.id,
            **params
        })
        while True:
            r = c.get(url)
            self.assertLess(r.status_code, 400, f'{url} = {r.status}')
            if r.status_code // 100 == 2:
                if url.startswith('/web/login'):
                    location, url = self.do_login(c, r.data, user)
                    continue
                break

            location = r.headers['Location']
            redir = self._cleanup(location)
            assert url != redir, "redirection loop"
            url = redir
        return obj, location, r

    @mute_logger(
        'odoo.addons.base.models.res_users', # on every login ~25 lines
        'odoo.addons.base.models.ir_model', # on every ACL error ~15 lines
    )
    def test_mail_view_portal(self):
        # (user, login, {(logged, token): final URL}
        OBJECT_URL = '/web#model={model}&id={id}&active_id={id}&cids=1'
        PORTAL_URL = '/my/thing?model={model}&res_id={id}{token}'
        NO_ACCESS = '/web#action=mail.action_discuss'
        PORTAL_ROOT = '/my' # portal user gets bounced from /web to /my
        cases = [
            ('not_portal', 'admin', defaultdict(lambda: OBJECT_URL)),
            # admin always gets backend unless unlogged w/ a token
            ('portal', 'admin', defaultdict(lambda: OBJECT_URL, {
                (False, True): PORTAL_URL,
            })),
            ('not_portal', 'demo', defaultdict(lambda: NO_ACCESS)),
             # demo gets portal if token
            ('portal', 'demo', {
                (True, True): PORTAL_URL, # no access + token => portal
                (False, True): PORTAL_URL, # unlogged + token => portal
                (True, False): NO_ACCESS,
                (False, False): NO_ACCESS,
            }),
            ('not_portal', 'portal', defaultdict(lambda: PORTAL_ROOT)),
            ('portal', 'portal', {
                (True, True): PORTAL_URL,
                (False, True): PORTAL_URL,
                (True, False): PORTAL_ROOT,
                (False, False): PORTAL_ROOT,
            }),
        ]
        for mod, user, items in cases:
            for (logged, token) in product([True, False], [True, False]):
                result = items[logged, token]
                label = f"object={mod} user={user}{', logged' if logged else ''}{', token' if token else ''}"
                with self.subTest(label):
                    obj, url, _ = self.do_flow(f'test_portal.{mod}', user, login=logged, token=token)
                    url = url_parse(url).replace(scheme='', netloc='').to_url()
                    tok = ''
                    if token and 'access_token' in obj._fields:
                        tok = f'&access_token={obj.access_token}'
                    expected = result.format(model=obj._name, id=obj.id, token=tok)
                    self.assertEqual(url, expected)

        # supplementary: if portal user has access to the resource, then they
        # get a portal link with an access token
        self.env['ir.model.access'].create({
            'name': 'portal access',
            'model_id': self.env.ref('test_portal.model_test_portal_portal').id,
            'group_id': self.env.ref('base.group_portal').id,
            'perm_read': True,
        })
        with self.subTest("object=portal user=portal[acl+] logged"):
            obj, url, _ = self.do_flow('test_portal.portal', 'portal', login=True, token=False)
            tok = f'&access_token={obj.access_token}'
            self.assertEqual(
                self._cleanup(url),
                PORTAL_URL.format(model=obj._name, id=obj.id, token=tok),
            )

        with self.subTest("object=portal user=portal[acl+]"):
            obj, url, _ = self.do_flow('test_portal.portal', 'portal', login=False, token=False)
            tok = f'&access_token={obj.access_token}'
            self.assertEqual(
                self._cleanup(url),
                PORTAL_URL.format(model=obj._name, id=obj.id, token=tok),
            )
