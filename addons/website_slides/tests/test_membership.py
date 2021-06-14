# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website_slides.tests import common
from odoo.tests import tagged, users
from odoo.tests.common import HOST
from odoo.tools import config

@tagged('post_install', '-at_install')
class TestMembership(common.SlidesCase):

    @users('user_officer')
    def test_invite_to_course(self):
        user_portal_partner = self.user_portal.partner_id
        self.assertFalse(user_portal_partner.id in self.channel.partner_ids.ids)

        # Invite partner to course
        self.slide_channel_invite_wizard = self.env['slide.channel.invite'].create({
            'channel_id': self.channel.id,
            'partner_ids': [(6, 0, [self.user_portal.partner_id.id])],
        })
        self.slide_channel_invite_wizard.action_invite()

        # The partner should be in the attendees with invitation pending status
        user_portal_channel_partner = self.channel.channel_partner_ids.filtered(lambda p: p.partner_id.id == user_portal_partner.id)
        self.assertTrue(user_portal_channel_partner)
        self.assertTrue(self.channel.with_user(self.user_portal).is_member_invitation_pending)
        self.assertFalse(self.channel.with_user(self.user_portal).is_member)
        self.assertEqual(user_portal_channel_partner.member_status, 'invite_sent')

        # Do not subscribe invited members to the chatter
        self.assertFalse(user_portal_partner.id in self.channel.message_partner_ids.ids)

    @users('user_officer')
    def test_attendee_default_create(self):
        slide_channel_partner = self.env['slide.channel.partner'].create({
            'channel_id': self.channel.id,
            'partner_id': self.user_portal.partner_id.id
        })

        # By default, partner is enrolled and subscribed to chatter
        self.assertTrue(self.user_portal.partner_id.id in self.channel.message_partner_ids.ids)
        self.assertFalse(self.channel.with_user(self.user_portal).is_member_invitation_pending)
        self.assertTrue(self.channel.with_user(self.user_portal).is_member)
        self.assertEqual(slide_channel_partner.member_status, 'joined')

    @users('user_officer')
    def test_join_enroll_invite_channel(self):
        self.channel.write({'enroll': 'invite'})
        user_portal_partner = self.user_portal.partner_id

        # Uninvited partner cannot join the course
        self.channel.with_user(self.user_portal).action_add_member()
        self.assertFalse(user_portal_partner.id in self.channel.partner_ids.ids)

        user_portal_channel_partner = self.env['slide.channel.partner'].create({
            'channel_id': self.channel.id,
            'partner_id': user_portal_partner.id,
            'member_status': 'invite_sent'
        })

        # Invited partner can join the course and enroll itself. It is added in chatter subscribers
        self.channel.with_user(self.user_portal).action_add_member()
        self.assertTrue(user_portal_partner.id in self.channel.partner_ids.ids)
        self.assertFalse(user_portal_channel_partner.member_status == 'invite_sent')
        self.assertTrue(self.user_portal.partner_id.id in self.channel.message_partner_ids.ids)


@tagged('-at_install', 'post_install')
class TestMembershipCase(HttpCaseWithUserPortal):

    def setUp(self):
        super(TestMembershipCase, self).setUp()
        self.user_admin = self.env.ref('base.user_admin')
        self.channel = self.env['slide.channel'].with_user(self.user_admin).create({
            'name': 'All about member status - Members only',
            'channel_type': 'training',
            'enroll': 'public',
            'visibility': 'public',
            'is_published': True,
        })
        self.slide = self.env['slide.slide'].with_user(self.user_admin).create({
            'name': 'How to understand membership',
            'channel_id': self.channel.id,
            'slide_type': 'presentation',
            'is_published': True,
            'completion_time': 2.0,
            'sequence': 1,
        })

    def test_invite_route_members_only_course(self):
        ''' Invite route redirects properly the (not) logged user in a course with members-only visibility'''
        self.channel.write({'visibility': 'members'})
        invite_url = "/slides/%s/invite" % self.channel.id

        # No user logged
        res = self.url_open(invite_url)
        login_redirect_url = f'web/login?redirect=/slides/{self.channel.id}/invite'
        self.assertEqual(res.status_code, 200)
        self.assertTrue(login_redirect_url in res.url, "Should redirect to login page then invite route")

        # User logged but not invited nor enrolled
        self.authenticate("portal", "portal")
        res = self.url_open(invite_url)
        base_url = "http://%s:%s" % (HOST, config['http_port'])
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.url, f'{base_url}/slides', "Should redirect to main /slides page")

        # Logged user has a pending invitation to the course
        self.env['slide.channel.partner'].create({
            'channel_id': self.channel.id,
            'partner_id': self.user_portal.partner_id.id,
            'member_status': 'invite_sent'
        })
        res = self.url_open(invite_url)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(f'slides/{slug(self.channel)}' in res.url, "Should redirect to the course page")

    def test_invite_route_public_course(self):
        ''' Invite route redirects properly the (not) logged user in a course with public visibility'''
        invite_url = "/slides/%s/invite" % self.channel.id

        # No logged user
        res = self.url_open(invite_url)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(f'slides/{slug(self.channel)}' in res.url, "Should redirect to the course page")

        # Case logged in user not invited
        self.authenticate("portal", "portal")
        res = self.url_open(invite_url)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(f'slides/{slug(self.channel)}' in res.url, "Should redirect to the course page")
