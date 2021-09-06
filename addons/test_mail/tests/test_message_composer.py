# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from unittest.mock import patch

from odoo import tools
from odoo.addons.test_mail.tests.common import BaseFunctionalTest, MockEmails, TestRecipients
from odoo.addons.test_mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.models.test_mail_models import MailTestSimple
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('mail_composer')
class TestComposer(BaseFunctionalTest, MockEmails, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestComposer, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})

        # configure mailing
        cls.alias_domain = 'schlouby.fr'
        cls.alias_catchall = 'test+catchall'
        cls.env['ir.config_parameter'].set_param('mail.catchall.domain', cls.alias_domain)
        cls.env['ir.config_parameter'].set_param('mail.catchall.alias', cls.alias_catchall)

        # admin should not receive emails
        cls.user_admin.write({'notification_type': 'email'})

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_comment(self):
        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': self.test_record._name,
            'default_res_id': self.test_record.id,
        }).with_user(self.user_employee).create({
            'body': '<p>Test Body</p>',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })
        composer.send_mail()

        message = self.test_record.message_ids[0]
        self.assertEqual(message.body, '<p>Test Body</p>')
        self.assertEqual(message.author_id, self.user_employee.partner_id)
        self.assertEqual(message.subject, 'Re: %s' % self.test_record.name)
        self.assertEqual(message.subtype_id, self.env.ref('mail.mt_comment'))
        self.assertEqual(message.partner_ids, self.partner_1 | self.partner_2)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_comment_parent(self):
        parent = self.test_record.message_post(body='Test')

        self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_parent_id': parent.id
        }).with_user(self.user_employee).create({
            'body': '<p>Mega</p>',
        }).send_mail()

        message = self.test_record.message_ids[0]
        self.assertEqual(message.body, '<p>Mega</p>')
        self.assertEqual(message.parent_id, parent)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_mass_mail(self):
        test_record_2 = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Test2'})

        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': self.test_record._name,
            'default_res_id': False,
            'active_ids': [self.test_record.id, test_record_2.id]
        }).with_user(self.user_employee).create({
            'subject': 'Testing ${object.name}',
            'body': '<p>${object.name}</p>',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })
        composer.with_context({
            'default_res_id': -1,
            'active_ids': [self.test_record.id, test_record_2.id]
        }).send_mail()

        # check mail_mail
        mails = self.env['mail.mail'].search([('subject', 'ilike', 'Testing')])
        for mail in mails:
            self.assertEqual(mail.recipient_ids, self.partner_1 | self.partner_2,
                             'compose wizard: mail_mail mass mailing: mail.mail in mass mail incorrect recipients')

        # check message on test_record
        message1 = self.test_record.message_ids[0]
        self.assertEqual(message1.subject, 'Testing %s' % self.test_record.name)
        self.assertEqual(message1.body, '<p>%s</p>' % self.test_record.name)

        # check message on test_record_2
        message1 = test_record_2.message_ids[0]
        self.assertEqual(message1.subject, 'Testing %s' % test_record_2.name)
        self.assertEqual(message1.body, '<p>%s</p>' % test_record_2.name)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_mass_mail_active_domain(self):
        test_record_2 = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Test2'})

        self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': self.test_record._name,
            'default_use_active_domain': True,
            'active_ids': [self.test_record.id],
            'active_domain': [('name', 'in', ['%s' % self.test_record.name, '%s' % test_record_2.name])],
        }).with_user(self.user_employee).create({
            'subject': 'From Composer Test',
            'body': '${object.name}',
        }).send_mail()

        self.assertEqual(self.test_record.message_ids[0].subject, 'From Composer Test')
        self.assertEqual(test_record_2.message_ids[0].subject, 'From Composer Test')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_compose_mass_mail_no_active_domain(self):
        test_record_2 = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Test2'})

        self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': self.test_record._name,
            'default_use_active_domain': False,
            'active_ids': [self.test_record.id],
            'active_domain': [('name', 'in', ['%s' % self.test_record.name, '%s' % test_record_2.name])],
        }).with_user(self.user_employee).create({
            'subject': 'From Composer Test',
            'body': '${object.name}',
        }).send_mail()

        self.assertEqual(self.test_record.message_ids[0].subject, 'From Composer Test')
        self.assertFalse(test_record_2.message_ids.ids)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_compose_portal_ok(self):
        portal_user = mail_new_test_user(self.env, login='chell', groups='base.group_portal', name='Chell Gladys')

        with patch.object(MailTestSimple, 'check_access_rights', return_value=True):
            ComposerPortal = self.env['mail.compose.message'].with_user(portal_user)

            ComposerPortal.with_context({
                'default_composition_mode': 'comment',
                'default_model': self.test_record._name,
                'default_res_id': self.test_record.id,
            }).create({
                'subject': 'Subject',
                'body': '<p>Body text</p>',
                'partner_ids': []}).send_mail()

            self.assertEqual(self.test_record.message_ids[0].body, '<p>Body text</p>')
            self.assertEqual(self.test_record.message_ids[0].author_id, portal_user.partner_id)

            ComposerPortal.with_context({
                'default_composition_mode': 'comment',
                'default_parent_id': self.test_record.message_ids.ids[0],
            }).create({
                'subject': 'Subject',
                'body': '<p>Body text 2</p>'}).send_mail()

            self.assertEqual(self.test_record.message_ids[0].body, '<p>Body text 2</p>')
            self.assertEqual(self.test_record.message_ids[0].author_id, portal_user.partner_id)


@tagged('mail_composer')
class TestComposerWTpl(BaseFunctionalTest, MockEmails, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestComposerWTpl, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com',
        })

        cls.user_employee.write({
            'groups_id': [(4, cls.env.ref('base.group_partner_manager').id)],
        })

        cls._attachments = [{
            'name': 'first.txt',
            'datas': base64.b64encode(b'My first attachment'),
            'res_model': 'res.partner',
            'res_id': cls.user_admin.partner_id.id
        }, {
            'name': 'second.txt',
            'datas': base64.b64encode(b'My second attachment'),
            'res_model': 'res.partner',
            'res_id': cls.user_admin.partner_id.id
        }]

        cls.email_1 = 'test1@example.com'
        cls.email_2 = 'test2@example.com'
        cls.email_3 = cls.partner_1.email
        cls._create_template('mail.test.simple', {
            'attachment_ids': [(0, 0, cls._attachments[0]), (0, 0, cls._attachments[1])],
            'partner_to': '%s,%s' % (cls.partner_2.id, cls.user_admin.partner_id.id),
            'email_to': '%s, %s' % (cls.email_1, cls.email_2),
            'email_cc': '%s' % cls.email_3,
        })

        # admin should receive emails
        cls.user_admin.write({'notification_type': 'email'})
        # Force the attachments of the template to be in the natural order.
        cls.email_template.invalidate_cache(['attachment_ids'], ids=cls.email_template.ids)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_w_template(self):
        composer = self.env['mail.compose.message'].with_user(self.user_employee).with_context({
            'default_composition_mode': 'comment',
            'default_model': 'mail.test.simple',
            'default_res_id': self.test_record.id,
            'default_template_id': self.email_template.id,
        }).create({'subject': 'Forget me subject', 'body': 'Dummy body'})

        # perform onchange and send emails
        values = composer.onchange_template_id(self.email_template.id, 'comment', self.test_record._name, self.test_record.id)['value']
        composer.write(values)
        composer.send_mail()

        new_partners = self.env['res.partner'].search([('email', 'in', [self.email_1, self.email_2])])
        self.assertEmails(
            self.user_employee.partner_id,
            [[self.partner_1], [self.partner_2], [new_partners[0]], [new_partners[1]], [self.partner_admin]],
            subject='About %s' % self.test_record.name,
            body_content=self.test_record.name,
            attachments=[('first.txt', b'My first attachment', 'text/plain'), ('second.txt', b'My second attachment', 'text/plain')])

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_w_template_email_field(self):
        """ Test various combinations of corner case / not standard filling of
        email fields: multi email, formatted emails, ... """
        existing_partners = self.env['res.partner'].search([])
        self.email_template.write({
            'email_cc': '"Raoul" <test.cc.1@example.com>, invalid',
            'email_from': '${user.email_formatted | safe}',
            'email_to': '"Micheline, l\'Immense" <test.to.1@example.com>, test.to.2@example.com, wrong',
            'partner_to': '%s,%s,%s' % (self.partner_1.id, self.partner_2.id, 0)
        })
        self.user_employee.write({'email': 'email.from.1@test.example.com, email.from.2@test.example.com'})
        self.partner_1.write({'email': '"Valid Formatted" <valid.lelitre@agrolait.com>'})
        self.partner_2.write({'email': 'valid.other.1@agrolait.com, valid.other.cc@agrolait.com'})

        composer = self.env['mail.compose.message'].with_user(self.user_employee).with_context({
            'default_composition_mode': 'comment',
            'default_model': 'mail.test.simple',
            'default_res_id': self.test_record.id,
            'default_template_id': self.email_template.id,
        }).create({'subject': 'Forget me subject', 'body': 'Dummy body'})

        # perform onchange and send emails
        composer.write(
            composer.onchange_template_id(
                self.email_template.id, 'comment', self.test_record._name, self.test_record.id
            )['value']
        )
        composer.send_mail()

        # find partners created during sending (as emails are transformed into partners)
        new_partners = self.env['res.partner'].search([]).search([('id', 'not in', existing_partners.ids)])
        self.assertEqual(
            sorted(new_partners.mapped('email')),
            sorted(['test.cc.1@example.com', 'test.to.1@example.com', 'test.to.2@example.com']),
            'Mail: created partners for valid emails (wrong / invalid not taken into account)'
        )
        self.assertEqual(
            sorted(new_partners.mapped('name')),
            sorted(['test.cc.1@example.com', 'test.to.1@example.com', 'test.to.2@example.com']),
            'Mail: currently setting name = email, not taking into account formatted emails'
        )
        # specific for customer with formatted email
        partner1_email = next(
            (mail for mail in self._mails
             if mail['email_to'] == [tools.formataddr((self.partner_1.name, '"Valid Formatted" <valid.lelitre@agrolait.com>'))]),
            False
        )
        self.assertTrue(partner1_email,
                       'Mail: sent an email to a broken address: double encapsulation of emails ("Tony" <"Formatted" <tony@e.com>>)')
        # specific for customer with multiple email
        partner2_email = next(
            (mail for mail in self._mails
             if mail['email_to'] == [tools.formataddr((self.partner_2.name, 'valid.other.1@agrolait.com, valid.other.cc@agrolait.com'))]),
            False
        )
        self.assertTrue(partner2_email,
                        'Mail: sent an email to an invalid multi-emails ("Tony" <tony@e.com, tony2@e.com>), not valid but some providers support it')
        # other emails
        self._mails = [mail for mail in self._mails if mail not in [partner1_email, partner2_email]]
        self.assertEmails(
            self.user_employee.partner_id,
            new_partners,
            email_cc=[],  # cc are transformed into To
            # from keeps multi email
            email_from=tools.formataddr((self.user_employee.name, 'email.from.1@test.example.com, email.from.2@test.example.com')),
        )

    def test_composer_template_onchange_attachments(self):
        """Tests that all attachments are added to the composer,
        static attachments are not duplicated and while reports are re-generated,
        and that intermediary attachments are dropped."""

        composer = self.env['mail.compose.message'].with_context(default_attachment_ids=[]).create({})
        report_template = self.env.ref('web.action_report_externalpreview')
        template_1 = self.email_template.copy({
            'report_template': report_template.id,
        })
        template_2 = self.email_template.copy({
            'attachment_ids': False,
            'report_template': report_template.id,
        })

        onchange_templates = [template_1, template_2, template_1, False]
        attachments_onchange = [composer.attachment_ids]
        # template_1 has two static attachments and one dynamically generated report,
        # template_2 only has the report, so we should get 3, 1, 3 attachments
        attachment_numbers = [0, 3, 1, 3, 0]

        for template in onchange_templates:
            onchange = composer.onchange_template_id(
                template.id if template else False, 'comment', self.test_record._name, self.test_record.id
            )
            composer.update(onchange['value'])
            attachments_onchange.append(composer.attachment_ids)

        self.assertEqual(
            [len(attachments) for attachments in attachments_onchange],
            attachment_numbers,
        )

        self.assertTrue(
            len(attachments_onchange[1] & attachments_onchange[3]) == 2,
            "The two static attachments on the template should be common to the two onchanges"
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_w_template_mass_mailing(self):
        test_record_2 = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Test2', 'email_from': 'laurie.poiret@example.com'})

        composer = self.env['mail.compose.message'].with_user(self.user_employee).with_context({
            'default_composition_mode': 'mass_mail',
            # 'default_notify': True,
            'default_notify': False,
            'default_model': 'mail.test.simple',
            'default_res_id': self.test_record.id,
            'default_template_id': self.email_template.id,
            'active_ids': [self.test_record.id, test_record_2.id]
        }).create({})
        values = composer.onchange_template_id(self.email_template.id, 'mass_mail', 'mail.test.simple', self.test_record.id)['value']
        composer.write(values)
        composer.send_mail()

        new_partners = self.env['res.partner'].search([('email', 'in', [self.email_1, self.email_2])])
        # hack to use assertEmails
        self._mails_record1 = [dict(mail) for mail in self._mails if '%s-%s' % (self.test_record.id, self.test_record._name) in mail['message_id']]
        self._mails_record2 = [dict(mail) for mail in self._mails if '%s-%s' % (test_record_2.id, test_record_2._name) in mail['message_id']]

        self._mails = self._mails_record1
        self.assertEmails(
            self.user_employee.partner_id,
            [[self.partner_1], [self.partner_2], [new_partners[0]], [new_partners[1]], [self.partner_admin]],
            subject='About %s' % self.test_record.name,
            body_content=self.test_record.name,
            attachments=[('first.txt', b'My first attachment', 'text/plain'), ('second.txt', b'My second attachment', 'text/plain')])

        self._mails = self._mails_record2
        self.assertEmails(
            self.user_employee.partner_id,
            [[self.partner_1], [self.partner_2], [new_partners[0]], [new_partners[1]], [self.partner_admin]],
            subject='About %s' % test_record_2.name,
            body_content=test_record_2.name,
            attachments=[('first.txt', b'My first attachment', 'text/plain'), ('second.txt', b'My second attachment', 'text/plain')])

        message_1 = self.test_record.message_ids[0]
        message_2 = test_record_2.message_ids[0]

        # messages effectively posted
        self.assertEqual(message_1.subject, 'About %s' % self.test_record.name)
        self.assertEqual(message_2.subject, 'About %s' % test_record_2.name)
        self.assertIn(self.test_record.name, message_1.body)
        self.assertIn(test_record_2.name, message_2.body)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_w_template_mass_mailing_email_field(self):
        """ Test various combinations of corner case / not standard filling of
        email fields: multi email, formatted emails, ... """
        test_record_2 = self.env['mail.test.simple'].with_context(self._test_context).create({
            'email_from': 'laurie.poiret@example.com',
            'name': 'Test2',
        })
        existing_partners = self.env['res.partner'].search([])

        self.email_template.write({
            'email_cc': '"Raoul" <test.cc.1@example.com>, invalid',
            'email_from': '${user.email_formatted | safe}',
            'email_to': '"Micheline, l\'Immense" <test.to.1@example.com>, test.to.2@example.com, wrong',
            'partner_to': '%s,%s,%s' % (self.partner_1.id, self.partner_2.id, 0)
        })
        self.user_employee.write({'email': 'email.from.1@test.example.com, email.from.2@test.example.com'})
        self.partner_1.write({'email': '"Valid Formatted" <valid.lelitre@agrolait.com>'})
        self.partner_2.write({'email': 'valid.other.1@agrolait.com, valid.other.cc@agrolait.com'})

        composer = self.env['mail.compose.message'].with_user(self.user_employee).with_context({
            'active_ids': [self.test_record.id, test_record_2.id],
            'default_composition_mode': 'mass_mail',
            'default_model': 'mail.test.simple',
            'default_notify': False,
            'default_res_id': self.test_record.id,
            'default_template_id': self.email_template.id,
        }).create({})
        composer.write(
            composer.onchange_template_id(
                self.email_template.id, 'mass_mail', 'mail.test.simple', self.test_record.id
            )['value']
        )
        composer.send_mail()

        # find partners created during sending (as emails are transformed into partners)
        new_partners = self.env['res.partner'].search([]).search([('id', 'not in', existing_partners.ids)])
        self.assertEqual(
            sorted(new_partners.mapped('email')),
            sorted(['test.cc.1@example.com', 'test.to.1@example.com', 'test.to.2@example.com']),
            'Mail: created partners for valid emails (wrong / invalid not taken into account)'
        )
        self.assertEqual(
            sorted(new_partners.mapped('name')),
            sorted(['test.cc.1@example.com', 'test.to.1@example.com', 'test.to.2@example.com']),
            'Mail: currently setting name = email, not taking into account formatted emails'
        )

        # hack to use assertEmails
        _mails_record1 = [mail for mail in self._mails if '%s-%s' % (self.test_record.id, self.test_record._name) in mail['message_id']]
        _mails_record2 = [mail for mail in self._mails if '%s-%s' % (test_record_2.id, test_record_2._name) in mail['message_id']]
        for record, mails in zip(
                self.test_record + test_record_2,
                [_mails_record1, _mails_record2]
            ):
            # specific for customer with formatted email
            partner1_email = next(
                (mail for mail in mails
                 if mail['email_to'] == [tools.formataddr((self.partner_1.name, '"Valid Formatted" <valid.lelitre@agrolait.com>'))]),
                False
            )
            self.assertTrue(partner1_email, 
                            'Mail: sent an email to a broken address: double encapsulation of emails ("Tony" <"Formatted" <tony@e.com>>)')
            # specific for customer with multiple email
            partner2_email = next(
                (mail for mail in mails
                 if mail['email_to'] == [tools.formataddr((self.partner_2.name, 'valid.other.1@agrolait.com, valid.other.cc@agrolait.com'))]),
                False
            )
            self.assertTrue(partner2_email,
                            'Mail: sent an email to an invalid multi-emails ("Tony" <tony@e.com, tony2@e.com>), not valid but some providers support it')
            # other emails
            self._mails = [mail for mail in mails if mail not in [partner1_email, partner2_email]]
            self.assertEmails(
                self.user_employee.partner_id,
                new_partners,
                subject='About %s' % record.name,
                body_content=record.name,
                attachments=[('first.txt', b'My first attachment', 'text/plain'),
                             ('second.txt', b'My second attachment', 'text/plain')],
                email_cc=[],  # cc are transformed into To
                # from keeps multi email
                email_from=tools.formataddr((self.user_employee.name, 'email.from.1@test.example.com, email.from.2@test.example.com')),
            )

    def test_composer_template_save(self):
        self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': 'mail.test.simple',
            'default_res_id': self.test_record.id,
        }).create({
            'subject': 'Forget me subject',
            'body': '<p>Dummy body</p>'
        }).save_as_template()
        # Test: email_template subject, body_html, model
        last_template = self.env['mail.template'].search([('model', '=', 'mail.test.simple'), ('subject', '=', 'Forget me subject')], limit=1)
        self.assertEqual(last_template.body_html, '<p>Dummy body</p>', 'email_template incorrect body_html')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_compose_notification_delete(self):
        # Mail notification should be deleted after being sent if
        # no mail template is not set on composer
        self.env['mail.compose.message'].with_context({
            'default_model': self.test_record._name,
            'default_res_id': self.test_record.id,
        }).with_user(self.user_employee).create({
            'body': '<p>Body Text</p>',
            'partner_ids': [(4, self.partner_1.id)]
        }).send_mail()
        message = self.test_record.message_ids[0]

        self.assertFalse(message.mail_ids,
                         'message_post: mail.mail notifications should have been auto-deleted')

        # Mail notification should be deleted after being sent auto_delete
        # is set to 'True'(which is default value) in mail template
        mail_template = self.env['mail.template'].create({
            'name': 'MAIL NOTIFICATION TEST',
            'subject': 'Test mail notification',
            'model_id': self.env.ref('test_mail.model_mail_test').id,
            'body_html': '<p>Body Text 2</p>',
        })

        self.env['mail.compose.message'].with_context({
            'default_model': self.test_record._name,
            'default_res_id': self.test_record.id,
            'default_template_id': mail_template.id,
        }).with_user(self.user_employee).create({
            'partner_ids': [(4, self.partner_1.id)]
        }).send_mail()
        message = self.test_record.message_ids[0]

        self.assertFalse(message.mail_ids,
                         'message_post: mail.mail notifications should have been auto-deleted')

        # Mail notification should not be deleted after being sent
        # if auto_delete is set to 'False' in mail template
        mail_template.auto_delete = False

        self.env['mail.compose.message'].with_context({
            'default_model': self.test_record._name,
            'default_res_id': self.test_record.id,
            'default_template_id': mail_template.id,
        }).with_user(self.user_employee).create({
            'partner_ids': [(4, self.partner_1.id)]
        }).send_mail()
        message = self.test_record.message_ids[0]

        self.assertEqual(len(message.mail_ids), 1,
                         'message_post: mail.mail notifications should have been kept')
