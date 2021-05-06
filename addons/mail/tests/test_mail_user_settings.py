# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import users

class TestMailUserSettings(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailUserSettings, cls).setUpClass()

    @users('employee')
    def test_get_category_states_should_create_new_settings_if_not_existing(self):
        settings = self.env['mail.user.settings'].search([
            ('user_id', '=', self.user_employee.id)
        ], limit=1)
        self.assertFalse(settings, "no records should exist")

        self.env['mail.user.settings'].get_category_states()
        settings =  self.env['mail.user.settings'].search([
            ('user_id', '=', self.user_employee.id)
        ], limit=1)
        self.assertTrue(settings, "a record should be created after get_category_states is called")

    @users('employee')
    def test_get_category_states_should_return_category_open_states(self):
        self.env['mail.user.settings'].create({
            'is_category_channel_open': False,
            'is_category_chat_open': True,
            'user_id': self.user_employee.id,
        })
        states = self.env['mail.user.settings'].get_category_states()
        self.assertEqual(
            states['is_category_channel_open'],
            False,
            'info should contain correct channel state'
        )
        self.assertEqual(
            states['is_category_chat_open'],
            True,
            'info should contain correct chat state'
        )

    @users('employee')
    def test_set_category_state_should_create_new_settings_if_not_existing(self):
        settings = self.env['mail.user.settings'].search([
            ('user_id', '=', self.user_employee.id)
        ], limit=1)
        self.assertFalse(settings, "no records should exist")

        self.env['mail.user.settings'].set_category_state('chat', True)
        settings =  self.env['mail.user.settings'].search([
            ('user_id', '=', self.user_employee.id)
        ], limit=1)
        self.assertTrue(settings, "a record should be created after set_category_states is called")

    @users('employee')
    def test_set_category_state_should_send_notification_on_bus(self):
        self.env['mail.user.settings'].create({
            'is_category_channel_open': False,
            'is_category_chat_open': False,
            'user_id': self.user_employee.id,
        })

        with self.assertBus([(self.cr.dbname, 'res.partner', self.partner_employee.id)]):
            self.env['mail.user.settings'].set_category_state('chat', True)

    @users('employee')
    def test_set_category_state_should_set_category_state_properly(self):
        self.env['mail.user.settings'].create({
            'is_category_channel_open': False,
            'is_category_chat_open': False,
            'user_id': self.user_employee.id,
        })

        settings =  self.env['mail.user.settings'].search([
            ('user_id', '=', self.user_employee.id)
        ], limit=1)
        self.env['mail.user.settings'].set_category_state('chat', True)
        self.assertEqual(
            settings.is_category_chat_open,
            True,
            "category state should be updated correctly"
        )
