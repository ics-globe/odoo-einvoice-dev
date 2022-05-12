# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.digest.tests.common import TestDigestCommon


class TestDigest(TestDigestCommon):

    @classmethod
    def setUpClass(cls):
        super(TestDigest, cls).setUpClass()

        cls.company_1 = cls.env.company
        cls.company_2 = cls.env['res.company'].create({'name': 'Digest Company 2'})

        context = {
            'start_datetime': datetime.now() - relativedelta(days=1),
            'end_datetime': datetime.now() + relativedelta(days=1),
        }

        cls.all_digests = cls.env['digest.digest'].with_context(context).create([{
            'name': 'Digest 1',
            'company_id': cls.env.company.id
        }, {
            'name': 'Digest 2',
            'company_id': cls.company_2.id
        }, {
            'name': 'Digest 3',
            'company_id': False
        }])

        cls.digest_1, cls.digest_2, cls.digest_3 = cls.all_digests

    def test_kpi_mail_message_total_value(self):
        # Sanity check
        initial_values = self.all_digests.mapped('kpi_mail_message_total_value')
        self.assertEqual(len(set(initial_values)), 1, 'Message Count is a cross company KPI')

        self.env['mail.message'].create([{
            'message_type': 'email',
            'subtype_id': self.env.ref('mail.mt_comment').id
        }, {
            'message_type': 'notification',
            'subtype_id': self.env.ref('mail.mt_comment').id
        }])

        self.all_digests.invalidate_cache(ids=self.all_digests.ids)

        values = self.all_digests.mapped('kpi_mail_message_total_value')

        self.assertEqual(len(set(values)), 1, 'Message Count is a cross company KPI')
        self.assertEqual(initial_values[0] + 1, values[0])

    def test_kpi_res_users_connected_value(self):
        # Sanity check
        initial_values = self.all_digests.mapped('kpi_res_users_connected_value')
        self.assertEqual(initial_values, [0, 0, 0])

        self.env['res.users.log'].with_user(self.user_employee).create({})
        self.env['res.users.log'].with_user(self.user_admin).create({})

        self.all_digests.invalidate_cache(ids=self.all_digests.ids)

        self.assertEqual(self.digest_1.kpi_res_users_connected_value, 2)
        self.assertEqual(self.digest_2.kpi_res_users_connected_value, 0,
            msg='This KPI is in an other company')
        self.assertEqual(self.digest_3.kpi_res_users_connected_value, 2,
            msg='This KPI has no company, should take the current one')
