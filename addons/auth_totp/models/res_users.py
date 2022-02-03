# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import babel.dates
import base64
import functools
import logging
import os
import re

from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.addons.base.models.res_users import check_identity
from odoo.exceptions import AccessDenied, UserError
from odoo.http import request
from odoo.tools import babel_locale_parse, hmac

from odoo.addons.auth_totp.models.totp import hotp, TIMESTEP, TOTP, TOTP_SECRET_SIZE

_logger = logging.getLogger(__name__)

TOTP_RATE_LIMITS = {
    'send_email': (10, 3600),
    'code_check': (10, 3600),
}

compress = functools.partial(re.sub, r'\s', '')
class Users(models.Model):
    _inherit = 'res.users'

    totp_secret = fields.Char(copy=False, groups=fields.NO_ACCESS)
    totp_enabled = fields.Boolean(string="Two-factor authentication", compute='_compute_totp_enabled')
    totp_trusted_device_ids = fields.One2many('auth_totp.device', 'user_id', string="Trusted Devices")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['totp_enabled', 'totp_trusted_device_ids']

    def _mfa_type(self):
        r = super()._mfa_type()
        if r is not None:
            return r
        if self.totp_enabled:
            return 'totp'
        otp_required = False
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('auth_totp.policy') == 'all_required':
            otp_required = True
        elif ICP.get_param('auth_totp.policy') == 'employee_required' and self.has_group('base.group_user'):
            otp_required = True
        if otp_required:
            return 'totp_mail'

    def _mfa_url(self):
        r = super()._mfa_url()
        if r is not None:
            return r
        if self._mfa_type() in ('totp', 'totp_mail'):
            return '/web/login/totp'

    @api.depends('totp_secret')
    def _compute_totp_enabled(self):
        for r, v in zip(self, self.sudo()):
            r.totp_enabled = bool(v.totp_secret)

    def _rpc_api_keys_only(self):
        # 2FA enabled means we can't allow password-based RPC
        self.ensure_one()
        return self.totp_enabled or super()._rpc_api_keys_only()

    def _get_session_token_fields(self):
        return super()._get_session_token_fields() | {'totp_secret'}

    def _totp_check(self, code):
        self._totp_rate_limit('code_check')
        sudo = self.sudo()
        if sudo._mfa_type() == 'totp':
            key = base64.b32decode(sudo.totp_secret)
            window = timestep = TIMESTEP
        else:
            key = self._get_totp_mail_key()
            window = timestep = 3600

        match = TOTP(key).match(code, window=window, timestep=timestep)
        if match is None:
            _logger.info("2FA check: FAIL for %s %r", self, self.login)
            raise AccessDenied(_("Verification failed, please double-check the 6-digit code"))
        _logger.info("2FA check: SUCCESS for %s %r", self, self.login)

        self._totp_rate_limit_purge('code_check')
        self._totp_rate_limit_purge('send_email')

    def _totp_try_setting(self, secret, code):
        if self.totp_enabled or self != self.env.user:
            _logger.info("2FA enable: REJECT for %s %r", self, self.login)
            return False

        secret = compress(secret).upper()
        match = TOTP(base64.b32decode(secret)).match(code)
        if match is None:
            _logger.info("2FA enable: REJECT CODE for %s %r", self, self.login)
            return False

        self.sudo().totp_secret = secret
        if request:
            self.flush()
            # update session token so the user does not get logged out (cache cleared by change)
            new_token = self.env.user._compute_session_token(request.session.sid)
            request.session.session_token = new_token

        _logger.info("2FA enable: SUCCESS for %s %r", self, self.login)
        return True

    @check_identity
    def action_totp_disable(self):
        logins = ', '.join(map(repr, self.mapped('login')))
        if not (self == self.env.user or self.env.user._is_admin() or self.env.su):
            _logger.info("2FA disable: REJECT for %s (%s) by uid #%s", self, logins, self.env.user.id)
            return False

        self.revoke_all_devices()
        self.sudo().write({'totp_secret': False})

        if request and self == self.env.user:
            self.flush()
            # update session token so the user does not get logged out (cache cleared by change)
            new_token = self.env.user._compute_session_token(request.session.sid)
            request.session.session_token = new_token

        _logger.info("2FA disable: SUCCESS for %s (%s) by uid #%s", self, logins, self.env.user.id)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'warning',
                'message': _("Two-factor authentication disabled for the following user(s): %s", ', '.join(self.mapped('name'))),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    @check_identity
    def action_totp_enable_wizard(self):
        if self.env.user != self:
            raise UserError(_("Two-factor authentication can only be enabled for yourself"))

        if self.totp_enabled:
            raise UserError(_("Two-factor authentication already enabled"))

        secret_bytes_count = TOTP_SECRET_SIZE // 8
        secret = base64.b32encode(os.urandom(secret_bytes_count)).decode()
        # format secret in groups of 4 characters for readability
        secret = ' '.join(map(''.join, zip(*[iter(secret)]*4)))
        w = self.env['auth_totp.wizard'].create({
            'user_id': self.id,
            'secret': secret,
        })
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_model': 'auth_totp.wizard',
            'name': _("Two-Factor Authentication Activation"),
            'res_id': w.id,
            'views': [(False, 'form')],
            'context': self.env.context,
        }

    @check_identity
    def revoke_all_devices(self):
        self._revoke_all_devices()

    def _revoke_all_devices(self):
        self.totp_trusted_device_ids._remove()

    @api.model
    def change_password(self, old_passwd, new_passwd):
        self.env.user._revoke_all_devices()
        return super().change_password(old_passwd, new_passwd)

    def action_open_my_account_settings(self):
        action = {
            "name": _("Account Security"),
            "type": "ir.actions.act_window",
            "res_model": "res.users",
            "views": [[self.env.ref('auth_totp.res_users_view_form').id, "form"]],
            "res_id": self.id,
        }
        return action

    def get_totp_invite_url(self):
        return '/web#action=auth_totp.action_activate_two_factor_authentication'

    def action_totp_invite(self):
        invite_template = self.env.ref('auth_totp.mail_template_totp_invite')
        users_to_invite = self.sudo().filtered(lambda user: not user.totp_secret)
        for user in users_to_invite:
            email_values = {
                'email_from': self.env.user.email_formatted,
                'author_id': self.env.user.partner_id.id,
            }
            invite_template.send_mail(user.id, force_send=True, email_values=email_values,
                                      email_layout_xmlid='mail.mail_notification_light')

        # Display a confirmation toaster
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'sticky': False,
                'message': _("Invitation to use two-factor authentication sent for the following user(s): %s",
                             ', '.join(users_to_invite.mapped('name'))),
            }
        }

    def _get_totp_mail_key(self):
        self.ensure_one()
        return hmac(self.env(su=True), 'auth_totp_mail-code', (self.id, self.login, self.login_date)).encode()

    def _get_totp_mail_code(self):
        self.ensure_one()

        key = self._get_totp_mail_key()

        now = datetime.now()
        counter = int(datetime.timestamp(now) / 3600)

        code = hotp(key, counter)
        expiration = timedelta(seconds=3600)
        lang = babel_locale_parse(self.env.context.get('lang') or self.lang)
        expiration = babel.dates.format_timedelta(expiration, lang)

        return str(code).zfill(6), expiration

    def _send_totp_mail_code(self):
        self.ensure_one()
        self._totp_rate_limit('send_email')

        if not self.email:
            raise UserError(_("Cannot send email: user %s has no email address.", self.name))

        template = self.env.ref('auth_totp.mail_template_totp_mail_code').sudo()
        context = {}
        if request:
            geoip = request.session.geoip
            context.update({
                'location': f"{geoip['city']}, {geoip['country_name']}" if geoip else None,
                'device': request.httprequest.user_agent.platform.capitalize(),
                'browser': request.httprequest.user_agent.browser.capitalize(),
                'ip': request.httprequest.environ['REMOTE_ADDR'],
            })
        email_values = {
            'email_to': self.email,
            'email_cc': False,
            'auto_delete': True,
            'recipient_ids': [],
            'partner_ids': [],
            'scheduled_date': False,
        }
        with self.env.cr.savepoint():
            template.with_context(**context).send_mail(
                self.id, force_send=True, raise_exception=True, email_values=email_values, email_layout_xmlid='mail.mail_notification_light'
            )

    def _totp_rate_limit(self, limit_type):
        self.ensure_one()
        assert request, "A request is required to be able to rate limit TOTP related actions"
        limit, interval = TOTP_RATE_LIMITS.get(limit_type)
        RateLimitLog = self.env['auth.totp.rate.limit.log'].sudo()
        ip = request.httprequest.environ['REMOTE_ADDR']
        domain = [
            ('user_id', '=', self.id),
            ('create_date', '>=', datetime.now() - timedelta(seconds=interval)),
            ('limit_type', '=', limit_type),
            ('ip', '=', ip),
        ]
        count = RateLimitLog.search_count(domain)
        if count >= limit:
            descriptions = {
                'send_email': _('You reached the limit of authentication mails sent for your account'),
                'code_check': _('You reached the limit of code verifications for your account'),
            }
            description = descriptions.get(limit_type)
            raise AccessDenied(description)
        RateLimitLog.create({
            'user_id': self.id,
            'ip': ip,
            'limit_type': limit_type,
        })

    def _totp_rate_limit_purge(self, limit_type):
        self.ensure_one()
        assert request, "A request is required to be able to rate limit TOTP related actions"
        ip = request.httprequest.environ['REMOTE_ADDR']
        RateLimitLog = self.env['auth.totp.rate.limit.log'].sudo()
        RateLimitLog.search([
            ('user_id', '=', self.id),
            ('limit_type', '=', limit_type),
            ('ip', '=', ip),
        ]).unlink()
