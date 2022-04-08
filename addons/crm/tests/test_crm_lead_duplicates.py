# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests.common import tagged, users


@tagged('lead_manage')
class TestLeadConvert(TestCrmCommon):

    @users('user_sales_manager')
    def test_potential_duplicates(self):
        company = self.env['res.partner'].create({
            'name': 'My company',
            'email': 'mycompany@company.com',
            'is_company': True,
            'street': '57th Street',
            'city': 'New New York',
            'country_id': self.env.ref('base.us').id,
            'zip': '12345',
        })

        partner_1 = self.env['res.partner'].create({
            'name': 'Dave',
            'email': 'dave@odoo.com',
            'mobile': '+1 202 555 0123',
            'phone': False,
            'parent_id': company.id,
            'is_company': False,
            'street': 'Pearl street',
            'city': 'California',
            'country_id': self.env.ref('base.us').id,
            'zip': '95826',
        })
        partner_2 = self.env['res.partner'].create({
            'name': 'Eve',
            'email': 'eve@odoo.com',
            'mobile': '+1 202 555 3210',
            'phone': False,
            'parent_id': company.id,
            'is_company': False,
            'street': 'Wall street',
            'city': 'New York',
            'country_id': self.env.ref('base.us').id,
            'zip': '54321',
        })

        lead_1 = self.env['crm.lead'].create({
            'name': 'Lead 1',
            'type': 'lead',
            'partner_name': 'Alice',
            'email_from': 'alice@odoo.com',
        })
        lead_2 = self.env['crm.lead'].create({
            'name': 'Opportunity 1',
            'type': 'opportunity',
            'email_from': 'alice@odoo.com',
        })
        lead_3 = self.env['crm.lead'].create({
            'name': 'Opportunity 2',
            'type': 'opportunity',
            'email_from': 'alice@odoo.com',
        })
        lead_4 = self.env['crm.lead'].create({
            'name': 'Lead 2',
            'type': 'lead',
            'partner_name': 'Alice Doe'
        })
        lead_5 = self.env['crm.lead'].create({
            'name': 'Opportunity 3',
            'type': 'opportunity',
            'partner_name': 'Alice Doe'
        })
        lead_6 = self.env['crm.lead'].create({
            'name': 'Opportunity 4',
            'type': 'opportunity',
            'partner_name': 'Bob Doe'
        })
        lead_7 = self.env['crm.lead'].create({
            'name': 'Opportunity 5',
            'type': 'opportunity',
            'partner_name': 'Bob Doe',
            'email_from': 'bob@odoo.com',
        })
        lead_8 = self.env['crm.lead'].create({
            'name': 'Opportunity 6',
            'type': 'opportunity',
            'email_from': 'bob@mymail.com',
        })
        lead_9 = self.env['crm.lead'].create({
            'name': 'Opportunity 7',
            'type': 'opportunity',
            'email_from': 'alice@mymail.com',
        })
        lead_10 = self.env['crm.lead'].create({
            'name': 'Opportunity 8',
            'type': 'opportunity',
            'probability': 0,
            'active': False,
            'email_from': 'alice@mymail.com',
        })
        lead_11 = self.env['crm.lead'].create({
            'name': 'Opportunity 9',
            'type': 'opportunity',
            'contact_name': 'charlie'
        })
        lead_12 = self.env['crm.lead'].create({
            'name': 'Opportunity 10',
            'type': 'opportunity',
            'contact_name': 'Charlie Chapelin',
        })
        lead_13 = self.env['crm.lead'].create({
            'name': 'Opportunity 8',
            'type': 'opportunity',
            'partner_id': partner_1.id
        })
        lead_14 = self.env['crm.lead'].create({
            'name': 'Lead 3',
            'type': 'lead',
            'partner_id': partner_2.id
        })
        lead_15 = self.env['crm.lead'].create({
            'name': 'Lead 15',
            'type': 'lead',
            'phone': '(803)-456-6126',
            'partner_name': 'test partner 1',
        })
        lead_16 = self.env['crm.lead'].create({
            'name': 'Lead 16',
            'type': 'lead',
            'phone': '(803)-456-6126',
            'partner_name': 'test partner 2',
        })
        lead_17 = self.env['crm.lead'].create({
            'name': 'Lead 17',
            'type': 'lead',
            'mobile': '1234567890',
            'contact_name': 'test contact 1',
        })
        lead_18 = self.env['crm.lead'].create({
            'name': 'Lead 18',
            'type': 'lead',
            'mobile': '1234567890',
            'contact_name': 'test contact 2',
        })
        lead_19 = self.env['crm.lead'].create({
            'name': 'Lead 19',
            'type': 'lead',
            'mobile': '(803)-456-6126',
        })
        lead_20 = self.env['crm.lead'].create({
            'name': 'Lead 20',
            'type': 'lead',
            'phone': '1234567890',
        })

        self.assertEqual(lead_1 + lead_2 + lead_3, lead_1.duplicate_lead_ids)
        self.assertEqual(lead_1 + lead_2 + lead_3, lead_2.duplicate_lead_ids)
        self.assertEqual(lead_1 + lead_2 + lead_3, lead_3.duplicate_lead_ids)
        self.assertEqual(lead_4 + lead_5, lead_4.duplicate_lead_ids)
        self.assertEqual(lead_4 + lead_5, lead_5.duplicate_lead_ids)
        self.assertEqual(lead_6 + lead_7, lead_6.duplicate_lead_ids)
        self.assertEqual(lead_6 + lead_7, lead_7.duplicate_lead_ids)
        self.assertEqual(lead_8 + lead_9 + lead_10, lead_8.duplicate_lead_ids)
        self.assertEqual(lead_8 + lead_9 + lead_10, lead_9.duplicate_lead_ids)
        self.assertEqual(lead_8 + lead_9 + lead_10, lead_10.duplicate_lead_ids)
        self.assertEqual(lead_11 + lead_12, lead_11.duplicate_lead_ids)
        self.assertEqual(lead_12, lead_12.duplicate_lead_ids)
        self.assertEqual(lead_13 + lead_14, lead_13.duplicate_lead_ids)
        self.assertEqual(lead_13 + lead_14, lead_14.duplicate_lead_ids)
        self.assertEqual(lead_15 + lead_16 + lead_19, lead_15.duplicate_lead_ids)
        self.assertEqual(lead_15 + lead_16 + lead_19, lead_16.duplicate_lead_ids)
        self.assertEqual(lead_15 + lead_16 + lead_19, lead_19.duplicate_lead_ids)
        self.assertEqual(lead_17 + lead_18 + lead_20, lead_17.duplicate_lead_ids)
        self.assertEqual(lead_17 + lead_18 + lead_20, lead_18.duplicate_lead_ids)
        self.assertEqual(lead_17 + lead_18 + lead_20, lead_20.duplicate_lead_ids)

    @users('user_sales_manager')
    def test_potential_duplicates_with_invalid_email(self):
        lead_1 = self.env['crm.lead'].create({
            'name': 'Lead 1',
            'type': 'lead',
            'email_from': 'mail"1@mymail.com'
        })
        lead_2 = self.env['crm.lead'].create({
            'name': 'Opportunity 1',
            'type': 'opportunity',
            'email_from': 'mail2@mymail.com'
        })
        lead_3 = self.env['crm.lead'].create({
            'name': 'Opportunity 2',
            'type': 'lead',
            'email_from': 'odoo.com'
        })
        lead_4 = self.env['crm.lead'].create({
            'name': 'Opportunity 3',
            'type': 'opportunity',
            'email_from': 'odoo.com'
        })
        lead_5 = self.env['crm.lead'].create({
            'name': 'Opportunity 3',
            'type': 'opportunity',
            'email_from': 'myodoo.com'
        })

        self.assertEqual(lead_1 + lead_2, lead_1.duplicate_lead_ids)
        self.assertEqual(lead_1 + lead_2, lead_2.duplicate_lead_ids)
        self.assertEqual(lead_3 + lead_4 + lead_5, lead_3.duplicate_lead_ids)
        self.assertEqual(lead_3 + lead_4 + lead_5, lead_4.duplicate_lead_ids)
        self.assertEqual(lead_5, lead_5.duplicate_lead_ids)
