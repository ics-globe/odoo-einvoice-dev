# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from imaplib import IMAP4, IMAP4_SSL

from odoo import api, fields, models
from odoo.addons.fetchmail.models.fetchmail import MAIL_TIMEOUT


class FetchmailServer(models.Model):
    _name = 'fetchmail.server'
    _inherit = ['fetchmail.server', 'google.gmail.mixin']

    server_type = fields.Selection(selection_add=[('gmail', 'Gmail OAuth Authentication')], ondelete={'gmail': 'set default'})

    @api.onchange('server_type', 'is_ssl', 'object_id')
    def onchange_server_type(self):
        """Set the default configuration for a IMAP Gmail server."""
        if self.server_type == 'gmail':
            self.server = 'imap.gmail.com'
            self.is_ssl = True
            self.port = 993
        else:
            self.google_gmail_authorization_code = False
            self.google_gmail_refresh_token = False
            super(FetchmailServer, self).onchange_server_type()

    def connect(self):
        """Connect to the mail server.

        If the mail server is Gmail, we use the OAuth2 authentication protocol.
        """
        self.ensure_one()
        if self.server_type == 'gmail':
            if self.is_ssl:
                connection = IMAP4_SSL(self.server, int(self.port))
            else:
                connection = IMAP4(self.server, int(self.port))
            auth_string = self._generate_oauth2_string(self.user, self.google_gmail_refresh_token)
            connection.authenticate('XOAUTH2', lambda x: auth_string)
            connection.select('INBOX')
            connection.sock.settimeout(MAIL_TIMEOUT)
            return connection

        return super(FetchmailServer, self).connect()

    def _get_connection_type(self):
        """Return which connection must be used for this mail server (IMAP or POP).

        The Gmail mail server used an IMAP connection.
        """
        self.ensure_one()
        if self.server_type == 'gmail':
            return 'imap'

        return super(FetchmailServer, self)._get_connection_type()
