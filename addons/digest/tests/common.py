# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.mail.tests import common as mail_test


class TestDigestCommon(mail_test.MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestDigestCommon, cls).setUpClass()

        cls.company_1 = cls.env.company
        cls.company_2 = cls.env['res.company'].create({'name': 'Company 2'})

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
