# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo.tests import Form, users
from odoo.tools import convert_file
from odoo.exceptions import AccessError
from odoo.addons.mail.tests.common import MailCommon
from odoo.modules.module import get_module_resource


class TestMailTemplate(MailCommon):
    def _load(self, module, *args):
        convert_file(self.cr, module='mail',
                     filename=get_module_resource(module, *args),
                     idref={}, mode='init', noupdate=False, kind='test')

    @classmethod
    def setUpClass(cls):
        super(TestMailTemplate, cls).setUpClass()
        # Enable the Jinja rendering restriction
        cls.env['ir.config_parameter'].set_param('mail.restrict.template.rendering', True)
        cls.user_employee.groups_id -= cls.env.ref('mail.group_mail_template_editor')

        cls.mail_template = cls.env['mail.template'].create({
            'name': 'Test template',
            'subject': '{{ 1 + 5 }}',
            'body_html': '<t t-out="4 + 9"/>',
            'lang': '{{ object.lang }}',
            'auto_delete': True,
            'model_id': cls.env.ref('base.model_res_partner').id,
        })

    @users('employee')
    def test_mail_compose_message_content_from_template(self):
        form = Form(self.env['mail.compose.message'])
        form.template_id = self.mail_template
        mail_compose_message = form.save()

        self.assertEqual(mail_compose_message.subject, '6', 'We must trust mail template values')

    @users('employee')
    def test_mail_compose_message_content_from_template_mass_mode(self):
        mail_compose_message = self.env['mail.compose.message'].create({
            'composition_mode': 'mass_mail',
            'model': 'res.partner',
            'template_id': self.mail_template.id,
            'subject': '{{ 1 + 5 }}',
        })

        values = mail_compose_message.get_mail_values(self.partner_employee.ids)

        self.assertEqual(values[self.partner_employee.id]['subject'], '6', 'We must trust mail template values')
        self.assertIn('13', values[self.partner_employee.id]['body_html'], 'We must trust mail template values')

    def test_mail_template_acl(self):
        # Sanity check
        self.assertTrue(self.user_admin.has_group('mail.group_mail_template_editor'))
        self.assertFalse(self.user_employee.has_group('mail.group_mail_template_editor'))

        # Group System can create / write / unlink mail template
        mail_template = self.env['mail.template'].with_user(self.user_admin).create({'name': 'Test template'})
        self.assertEqual(mail_template.name, 'Test template')

        mail_template.with_user(self.user_admin).name = 'New name'
        self.assertEqual(mail_template.name, 'New name')

        # Standard employee can not
        with self.assertRaises(AccessError):
            self.env['mail.template'].with_user(self.user_employee).create({})

        with self.assertRaises(AccessError):
            mail_template.with_user(self.user_employee).name = 'Test write'

    def test_mail_template_reset(self):
        self._load('mail', 'tests', 'test_mail_template.xml')

        mail_template = self.env.ref('mail.mail_template_test').with_context(lang=self.env.user.lang)
        self.assertFalse(mail_template.is_template_modified, "Mail Template should not be modified")

        mail_template.write({
            'body_html': '<div>Hello</div>',
            'name': 'Mail: Mail Template',
            'subject': 'Test'
        })
        self.assertTrue(mail_template.is_template_modified, "Mail Template should be modified")

        mail_template.reset_template()
        self.assertEqual(mail_template.body_html.strip(), Markup('<div>Hello Odoo</div>'))
        self.assertEqual(mail_template.name, 'Mail: Test Mail Template')

        # subject is not there in the data file template, so it should not be reset
        self.assertEqual(mail_template.subject, 'Test', "Subject should not be reset")
        self.assertFalse(mail_template.is_template_modified, "Mail Template should not be modified")
