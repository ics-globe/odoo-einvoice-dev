# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('res_partner')
class TestPartner(TransactionCase):

    def test_email_formatted(self):
        """ Test various combinations of name / email, notably to check result
        of email_formatted field. """
        new_partner = self.env['res.partner'].create({
            'name': "Vlad the Impaler",
            'email': 'vlad.the.impaler@example.com'
        })
        self.assertEqual(
            new_partner.email_formatted, '"Vlad the Impaler" <vlad.the.impaler@example.com>',
            'Email formatted should be name <email>'
        )

        # multi create
        new_partners = self.env['res.partner'].create([{
            'name': "Vlad the Impaler",
            'email': 'vlad.the.impaler.%02d@example.com' % idx,
        } for idx in range(5)])
        self.assertEqual(
            sorted(new_partners.mapped('email_formatted')),
            sorted(['"Vlad the Impaler" <vlad.the.impaler.%02d@example.com>' % idx for idx in range(5)]),
            'Email formatted should be name <email>'
        )

        # test name_create with formatting / multi emails
        new_partner_id = self.env['res.partner'].name_create('Balázs <vlad.the.negociator@example.com>, vlad.the.impaler@example.com')[0]
        new_partner = self.env['res.partner'].browse(new_partner_id)
        self.assertEqual(new_partner.name, "Balázs")
        self.assertEqual(new_partner.email, "vlad.the.negociator@example.com")
        self.assertEqual(
            new_partner.email_formatted, '"Balázs" <vlad.the.negociator@example.com>',
            'Name_create should take first found email'
        )

        new_partner_id = self.env['res.partner'].name_create('Balázs <vlad.the.impaler@example.com>')[0]
        new_partner = self.env['res.partner'].browse(new_partner_id)
        self.assertEqual(new_partner.name, "Balázs")
        self.assertEqual(new_partner.email, "vlad.the.impaler@example.com")
        self.assertEqual(
            new_partner.email_formatted, '"Balázs" <vlad.the.impaler@example.com>',
            'Name_create should correctly compute name / email'
        )

        # check name / email updates
        new_partner.write({'name': 'Vlad the Impaler'})
        self.assertEqual(new_partner.email_formatted, '"Vlad the Impaler" <vlad.the.impaler@example.com>')
        new_partner.write({'name': 'Balázs'})
        self.assertEqual(new_partner.email_formatted, '"Balázs" <vlad.the.impaler@example.com>')
        new_partner.write({'email': "Vlad the Impaler <vlad.the.impaler@example.com>"})
        self.assertEqual(new_partner.email_formatted, '"Balázs" <vlad.the.impaler@example.com>')
        new_partner.write({'email': 'Balázs <balazs@adam.hu>'})
        self.assertEqual(new_partner.email_formatted, '"Balázs" <balazs@adam.hu>')

        # check multi emails
        new_partner.write({'email': 'vlad.the.impaler@example.com, vlad.the.dragon@example.com'})
        # self.assertEqual(new_partner.email_formatted, '"Balázs" <vlad.the.impaler@example.com>')
        self.assertEqual(
            new_partner.email_formatted, '"Balázs" <vlad.the.impaler@example.com,vlad.the.dragon@example.com>',
            'Currently keeping multi-emails enabled when possible for backward compatibility')
        self.assertEqual(new_partner.with_context(partner_email_single=True).email_formatted, '"Balázs" <vlad.the.impaler@example.com>')
        new_partner.write({'email': 'vlad.the.impaler.com, vlad.the.dragon@example.com'})
        self.assertEqual(new_partner.email_formatted, '"Balázs" <vlad.the.dragon@example.com>')
        new_partner.write({'email': 'vlad.the.impaler.com, "Vlad the Dragon" <vlad.the.dragon@example.com>'})
        self.assertEqual(new_partner.email_formatted, '"Balázs" <vlad.the.dragon@example.com>')

        # check false emails
        new_partner.write({'email': 'notanemail'})
        self.assertEqual(new_partner.email_formatted, '"Balázs" <notanemail>',
                         'Email formatted should keep wrong emails as it helps debugging / having information in mails, notifications and traces')

    def test_name_search(self):
        """ Check name_search on partner, especially with domain based on auto_join
        user_ids field. Check specific SQL of name_search correctly handle joined tables. """
        test_partner = self.env['res.partner'].create({'name': 'Vlad the Impaler'})
        test_user = self.env['res.users'].create({'name': 'Vlad the Impaler', 'login': 'vlad', 'email': 'vlad.the.impaler@example.com'})

        ns_res = self.env['res.partner'].name_search('Vlad', operator='ilike')
        self.assertEqual(set(i[0] for i in ns_res), set((test_partner | test_user.partner_id).ids))

        ns_res = self.env['res.partner'].name_search('Vlad', args=[('user_ids.email', 'ilike', 'vlad')])
        self.assertEqual(set(i[0] for i in ns_res), set(test_user.partner_id.ids))

    def test_company_change_propagation(self):
        """ Check propagation of company_id across children """
        User = self.env['res.users']
        Partner = self.env['res.partner']
        Company = self.env['res.company']

        company_1 = Company.create({'name': 'company_1'})
        company_2 = Company.create({'name': 'company_2'})

        test_partner_company = Partner.create({'name': 'This company'})
        test_user = User.create({'name': 'This user', 'login': 'thisu', 'email': 'this.user@example.com', 'company_id': company_1.id, 'company_ids': [company_1.id]})
        test_user.partner_id.write({'parent_id': test_partner_company.id})

        test_partner_company.write({'company_id': company_1.id})
        self.assertEqual(test_user.partner_id.company_id.id, company_1.id, "The new company_id of the partner company should be propagated to its children")

        test_partner_company.write({'company_id': False})
        self.assertFalse(test_user.partner_id.company_id.id, "If the company_id is deleted from the partner company, it should be propagated to its children")

        with self.assertRaises(UserError, msg="You should not be able to update the company_id of the partner company if the linked user of a child partner is not an allowed to be assigned to that company"), self.cr.savepoint():
            test_partner_company.write({'company_id': company_2.id})
