# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.addons.mass_mailing_sms.tests.common import MassSMSCommon
from odoo.addons.mass_mailing.tests.test_mailing_ab_testing import TestMailingABTesting
from odoo.tests import users, tagged


@tagged('post_install', '-at_install')
class TestSMSMailingABTesting(MassSMSCommon, TestMailingABTesting):
    def setUp(self):
        super().setUp()
        self.ab_testing_sms_mailing_1 = self.env['mailing.mailing'].create({
            'subject': 'A/B Testing SMS V1',
            'contact_list_ids': self.mailing_list.ids,
            'ab_testing_enabled': True,
            'ab_testing_pc': 10,
            'ab_testing_schedule_datetime': datetime.now(),
            'mailing_type': 'sms'
        })
        self.ab_testing_sms_mailing_2 = self.ab_testing_sms_mailing_1.copy({
            'subject': 'A/B Testing SMS V2',
            'ab_testing_pc': 20,
        })
        self.ab_testing_sms_campaign = self.ab_testing_sms_mailing_1.campaign_id
        self.ab_testing_sms_mailing_ids = self.ab_testing_sms_mailing_1 + self.ab_testing_sms_mailing_2
        self.ab_testing_sms_mailing_ids.invalidate_cache()

    @users('user_marketing')
    def test_ab_testing_sms(self):
        # mailing.mailing record with mailing_type mail and with same campaign_id
        # as of other ab_testing mailing.mailing sms record to check compare verson
        self.env['mailing.mailing'].create({
            'subject': 'A/B Testing Mail V1',
            'contact_list_ids': self.mailing_list.ids,
            'ab_testing_enabled': True,
            'ab_testing_pc': 10,
            'ab_testing_schedule_datetime': datetime.now(),
            'mailing_type': 'mail',
            'campaign_id': self.ab_testing_sms_campaign.id,
        })
        compare_version = self.ab_testing_sms_mailing_1.action_compare_versions()
        compare_version_record_count = self.env['mailing.mailing'].search_count(compare_version.get('domain'))
        # Record with mailing_type equals to mail should not be included in compare version count, doesn't matter
        # if campign_id is same
        self.assertEqual(compare_version_record_count, 2, 'Number of records should be according to mailing type')
