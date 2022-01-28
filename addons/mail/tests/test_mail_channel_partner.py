# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, UserError


class TestMailChannelMembers(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailChannelMembers, cls).setUpClass()

        cls.secret_group = cls.env['res.groups'].create({
            'name': 'Secret User Group',
        })
        cls.env['ir.model.data'].create({
            'name': 'secret_group',
            'module': 'mail',
            'model': cls.secret_group._name,
            'res_id': cls.secret_group.id,
        })

        cls.user_1 = mail_new_test_user(
            cls.env, login='user_1',
            name='User 1',
            groups='base.group_user,mail.secret_group')
        cls.user_2 = mail_new_test_user(
            cls.env, login='user_2',
            name='User 2',
            groups='base.group_user,mail.secret_group')
        cls.user_portal = mail_new_test_user(
            cls.env, login='user_portal',
            name='User Portal',
            groups='base.group_portal')
        cls.user_public = mail_new_test_user(
            cls.env, login='user_ublic',
            name='User Public',
            groups='base.group_public')

        cls.group_channel = cls.env['mail.channel'].create({
            'name': 'Group channel',
            'channel_type': 'channel',
            'group_public_id': cls.secret_group.id,
        })
        cls.public_channel = cls.env['mail.channel'].create({
            'name': 'Public channel of user 1',
            'channel_type': 'channel',
        })
        (cls.group_channel | cls.public_channel).channel_last_seen_partner_ids.unlink()

    # ------------------------------------------------------------
    # GROUP BASED CHANNELS
    # ------------------------------------------------------------

    def test_channel_group(self):
        """Test basics on group channel."""
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel.id)])
        self.assertFalse(channel_partners)

        # user 1 is in the group, he can join the channel
        self.group_channel.with_user(self.user_1).add_members(self.user_1.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        # user 3 is not in the group, he can not join
        with self.assertRaises(AccessError):
            self.group_channel.with_user(self.user_portal).add_members(self.user_portal.partner_id.ids)

        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel.id)])
        with self.assertRaises(AccessError):
            channel_partners.with_user(self.user_portal).partner_id = self.user_portal.partner_id

        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        # user 1 can not invite user 3 because he's not in the group
        with self.assertRaises(UserError):
            self.group_channel.with_user(self.user_1).add_members(self.user_portal.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        # but user 2 is in the group and can be invited by user 1
        self.group_channel.with_user(self.user_1).add_members(self.user_2.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.group_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id | self.user_2.partner_id)

    # ------------------------------------------------------------
    # PUBLIC CHANNELS
    # ------------------------------------------------------------

    def test_channel_public(self):
        """ Test access on public channels """
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.public_channel.id)])
        self.assertFalse(channel_partners)

        self.public_channel.with_user(self.user_1).add_members(self.user_1.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.public_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id)

        self.public_channel.with_user(self.user_2).add_members(self.user_2.partner_id.ids)
        channel_partners = self.env['mail.channel.partner'].search([('channel_id', '=', self.public_channel.id)])
        self.assertEqual(channel_partners.mapped('partner_id'), self.user_1.partner_id | self.user_2.partner_id)

        # portal/public users still cannot join a public channel, should go through dedicated controllers
        with self.assertRaises(AccessError):
            self.public_channel.with_user(self.user_portal).add_members(self.user_portal.partner_id.ids)
        with self.assertRaises(AccessError):
            self.public_channel.with_user(self.user_public).add_members(self.user_public.partner_id.ids)
