# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests.common import Form


class TestPartner(TestCrmCommon):

    def test_onchange_parent_sync_team(self):
        self.contact_company_1.write({'team_id': self.sales_team_1.id})
        partner_form = Form(self.env['res.partner'], 'base.view_partner_form')
        partner_form.parent_id = self.contact_company_1
        partner_form.company_type = 'person'
        partner_form.name = 'Philip'
        self.assertEqual(partner_form.team_id, self.contact_company_1.team_id)
