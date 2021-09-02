# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.test_ir_actions import TestServerActionsBase
from odoo.addons.test_mail.tests.common import TestMailCommon


class TestServerActionsEmail(TestMailCommon, TestServerActionsBase):

    def setUp(self):
        super(TestServerActionsEmail, self).setUp()
        self.template = self._create_template(
            'res.partner',
            {'email_from': '{{ object.user_id.email_formatted or object.company_id.email_formatted or user.email_formatted }}',
             'partner_to': '%s' % self.test_partner.id,
            }
        )

    def test_action_email(self):
        self.action.write({'state': 'email', 'template_id': self.template.id})
        self.action.with_context(self.context).run()
        # check an email is waiting for sending
        mail = self.env['mail.mail'].sudo().search([('subject', '=', 'About TestingPartner')])
        self.assertEqual(len(mail), 1)
        # check email content
        self.assertEqual(mail.body, '<p>Hello TestingPartner</p>')

    def test_action_followers(self):
        self.test_partner.message_unsubscribe(self.test_partner.message_partner_ids.ids)
        random_partner = self.env['res.partner'].create({'name': 'Thierry Wololo'})
        self.action.write({
            'state': 'followers',
            'partner_ids': [(4, self.env.ref('base.partner_admin').id), (4, random_partner.id)],
        })
        self.action.with_context(self.context).run()
        self.assertEqual(self.test_partner.message_partner_ids, self.env.ref('base.partner_admin') | random_partner)

    def test_action_message_post(self):
        self.action.write({'state': 'message_post', 'template_id': self.template.id})
        with self.assertSinglePostNotifications(
                [{'partner': self.test_partner, 'type': 'email', 'status': 'ready'}],
                message_info={'content': 'Hello %s' % self.test_partner.name,
                              'message_type': 'notification',
                              'subtype': 'mail.mt_comment',
                             }
            ):
            self.action.with_context(self.context).run()
        # NOTE: template using current user will have funny email_from
        self.assertEqual(self.test_partner.message_ids[0].email_from, self.partner_root.email_formatted)

    def test_action_next_activity(self):
        self.action.write({
            'state': 'next_activity',
            'activity_user_type': 'specific',
            'activity_type_id': self.env.ref('mail.mail_activity_data_meeting').id,
            'activity_summary': 'TestNew',
        })
        before_count = self.env['mail.activity'].search_count([])
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create next activity action correctly finished should return False')
        self.assertEqual(self.env['mail.activity'].search_count([]), before_count + 1)
        self.assertEqual(self.env['mail.activity'].search_count([('summary', '=', 'TestNew')]), 1)
