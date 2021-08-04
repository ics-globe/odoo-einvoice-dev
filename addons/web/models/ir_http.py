# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import json
import logging

import odoo
from odoo import api, models
from odoo.http import request
from odoo.tools import ustr
from odoo.tools.misc import str2bool
from odoo.addons.web.controllers.main import HomeStaticTemplateHelpers


_logger = logging.getLogger(__name__)

""" Debug mode is stored in session and should always be a string.
    It can be activated with an URL query string `debug=<mode>` where
    mode is either:
    - 'tests' to load tests assets
    - 'assets' to load assets non minified
    - any other truthy value to enable simple debug mode (to show some
      technical feature, to show complete traceback in frontend error..)
    - any falsy value to disable debug mode

    You can use any truthy/falsy value from `str2bool` (eg: 'on', 'f'..)
    Multiple debug modes can be activated simultaneously, separated with
    a comma (eg: 'tests, assets').
"""
ALLOWED_DEBUG_MODES = ['', '1', 'assets', 'tests']


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _pre_dispatch(cls, rule, args):
        super()._pre_dispatch(rule, args)
        debug = request.httprequest.args.get('debug', '')
        if debug:
            request.session['debug'] = ','.join(
                    mode if mode in ALLOWED_DEBUG_MODES
                else '1' if str2bool(mode, mode)
                else ''
                for mode in debug.split(',')
            )

    def webclient_rendering_context(self):
        return {
            'menu_data': request.env['ir.ui.menu'].load_menus(request.session.debug),
            'session_info': self.session_info(),
        }

    def session_info(self):
        uid = request.env.uid
        if uid is not None:
            user = request.env.user
        version_info = odoo.service.common.exp_version()

        IrConfigSudo = self.env['ir.config_parameter'].sudo()
        max_file_upload_size = int(IrConfigSudo.get_param(
            'web.max_file_upload_size',
            default=128 * 1024 * 1024,  # 128MiB
        ))

        session_info = {
            "uid": request.env.uid,
            "is_system": user._is_system() if uid else False,
            "is_admin": user._is_admin() if uid else False,
            "user_context": request.env.context if uid else {},
            "db": request.db,
            "server_version": version_info.get('server_version'),
            "server_version_info": version_info.get('server_version_info'),
            "support_url": "https://www.odoo.com/buy",
            "name": user.name if uid else '',
            "username": user.login if uid else '',
            "partner_display_name": user.partner_id.display_name if uid else '',
            "company_id": user.company_id.id if uid else None,  # YTI TODO: Remove this from the user contex if uid else Nonet
            "partner_id": user.partner_id.id if uid else None,
            "web.base.url": IrConfigSudo.get_param('web.base.url', default=''),
            "active_ids_limit": int(IrConfigSudo.get_param('web.active_ids_limit', default='20000')),
            'profile_session': request.session.profile_session,
            'profile_collectors': request.session.profile_collectors,
            'profile_params': request.session.profile_params,
            "max_file_upload_size": max_file_upload_size,
            "home_action_id": user.action_id.id if uid else None,
        }
        if uid and user.has_group('base.group_user'):
            # the following is only useful in the context of a webclient bootstrapping
            # but is still included in some other calls (e.g. '/web/session/authenticate')
            # to avoid access errors and unnecessary information, it is only included for users
            # with access to the backend ('internal'-type users)
            mods = odoo.conf.server_wide_modules or []
            if request.db:
                mods = list(request.registry._init_modules) + mods
            qweb_checksum = HomeStaticTemplateHelpers.get_qweb_templates_checksum(debug=request.session.debug, bundle="web.assets_qweb")
            lang = user_context.get("lang")
            translation_hash = request.env['ir.translation'].get_web_translations_hash(mods, lang)
            menus = request.env['ir.ui.menu'].load_menus(request.session.debug)
            ordered_menus = {str(k): v for k, v in menus.items()}
            menu_json_utf8 = json.dumps(ordered_menus, default=ustr, sort_keys=True).encode()
            cache_hashes = {
                "load_menus": hashlib.sha512(menu_json_utf8).hexdigest()[:64], # sha512/256
                "qweb": qweb_checksum,
                "translations": translation_hash,
            }
            session_info.update({
                # current_company should be default_company
                "user_companies": {
                    'current_company': user.company_id.id,
                    'allowed_companies': {
                        comp.id: {
                            'id': comp.id,
                            'name': comp.name,
                        } for comp in user.company_ids
                    },
                },
                "currencies": self.get_currencies(),
                "show_effect": True,
                "display_switch_company_menu": user.has_group('base.group_multi_company') and len(user.company_ids) > 1,
                "cache_hashes": cache_hashes,
            })
        return session_info

    @api.model
    def get_frontend_session_info(self):
        uid = self.env.uid
        if uid is not None:
            user = self.env.user

        session_info = {
            'is_admin': user._is_admin() if uid else False,
            'is_system': user._is_system() if uid else False,
            'is_website_user': user._is_public() if uid else False,
            'user_id': self.env.uid,
            'is_frontend': True,
            'profile_session': request.session.profile_session,
            'profile_collectors': request.session.profile_collectors,
            'profile_params': request.session.profile_params,
            'show_effect': request.env['ir.config_parameter'].sudo().get_param('base_setup.show_effect'),
        }
        if uid:
            version_info = odoo.service.common.exp_version()
            session_info.update({
                'server_version': version_info.get('server_version'),
                'server_version_info': version_info.get('server_version_info')
            })
        return session_info

    def get_currencies(self):
        Currency = request.env['res.currency']
        currencies = Currency.search([]).read(['symbol', 'position', 'decimal_places'])
        return {c['id']: {'symbol': c['symbol'], 'position': c['position'], 'digits': [69,c['decimal_places']]} for c in currencies}
