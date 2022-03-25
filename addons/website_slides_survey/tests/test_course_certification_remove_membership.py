# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.survey.tests.common import TestSurveyCommon


class TestCourseCertificationRemoveMembership(TestSurveyCommon):

    def setUp(self):
        super(TestCourseCertificationRemoveMembership, self).setUp()

        # Step 1: create a simple certification
        with self.with_user('survey_user'):
            self.certification = self.env['survey.survey'].create({
                'title': 'Small course certification',
                'access_mode': 'public',
                'users_login_required': True,
                'scoring_type': 'scoring_with_answers',
                'certification': True,
                'is_attempts_limited': True,
                'scoring_success_min': 100.0,
                'attempts_limit': 2,
            })

            self._add_question(
                None, 'Question 1', 'simple_choice',
                sequence=1,
                survey_id=self.certification.id,
                labels=[
                    {'value': 'Wrong answer'},
                    {'value': 'Correct answer', 'is_correct': True, 'answer_score': 1.0}
                ])

            self._add_question(
                None, 'Question 2', 'simple_choice',
                sequence=2,
                survey_id=self.certification.id,
                labels=[
                    {'value': 'Wrong answer'},
                    {'value': 'Correct answer', 'is_correct': True, 'answer_score': 1.0}
                ])

        # Step 1.1: create a simple channel
        self.channel = self.env['slide.channel'].sudo().create({
            'name': 'Test Channel',
            'channel_type': 'training',
            'enroll': 'public',
            'visibility': 'public',
            'is_published': True,
            'karma_gen_channel_finish': 10,
        })

        # Step 2: link the certification to a slide of category 'certification'
        self.slide_certification = self.env['slide.slide'].sudo().create({
            'name': 'Certification slide',
            'channel_id': self.channel.id,
            'slide_category': 'certification',
            'survey_id': self.certification.id,
            'is_published': True,
        })

    def test_course_certification_remove_membership(self):
        # add public user as member of the channel
        self.channel._action_add_members(self.user_public.partner_id)
        # forces recompute of partner_ids as we create directly in relation
        self.channel.invalidate_cache()
        self.assertIn(self.user_public.partner_id, self.channel.partner_ids, 'Public user should still be a member of the course because he still has attempts left')

        slide_partner = self.slide_certification._action_set_viewed(self.user_public.partner_id)

        channel_partner = self.env['slide.channel.partner'].search([
            ('channel_id', 'in', self.channel.ids),
            ('partner_id', 'in', slide_partner.partner_id.ids)
        ])
        self.slide_certification.with_user(self.user_public)._generate_certification_url()

        self.assertEqual(1, len(slide_partner.user_input_ids), 'A user input should have been automatically created upon slide view')

        self.channel._remove_membership(self.user_public.partner_id.ids)

        self.assertFalse(slide_partner.user_input_ids.active, 'An user input should be archived if User left the course')
        self.assertFalse(channel_partner.active, 'An Attendee should be archived if User left the course')

    def test_course_certification_karma(self):
        # add public user as member of the channel
        self.channel._action_add_members(self.user_public.partner_id)
        channel_partner = self.env['slide.channel.partner'].search([
            ('channel_id', 'in', self.channel.ids),
            ('partner_id', 'in', self.user_public.partner_id.ids)
        ])
        self.assertEqual(0, self.user_public.karma, 'User Karma should be 0')

        # Set Certification slide to completed to Gain Karma
        self.slide_certification.with_user(self.user_public).action_mark_completed()
        self.assertEqual(10, self.user_public.karma, 'User Karma should be updated to 10')

        # Removing of membership should remove Karma Gained from the Course
        self.channel._remove_membership(self.user_public.partner_id.ids)
        self.assertFalse(channel_partner.completed, 'Channel should be set to Uncompleted on Removing Membership')
        self.assertEqual(0, self.user_public.karma, 'User Karma should be reversed')

        # Add public user as member of the channel again
        self.channel._action_add_members(self.user_public.partner_id)

        # Set Certification slide to completed will Gain Karma again
        self.slide_certification.with_user(self.user_public).action_mark_completed()
        self.assertEqual(10, self.user_public.karma, 'User Karma should be updated to 10')
