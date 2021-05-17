# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests.common import Form, users


class TestMailingContactToList(MassMailCommon):

    @users('user_marketing')
    def test_mailing_contact_to_list(self):
        contacts = self.env['mailing.contact'].create([{
            'name': 'Contact %02d',
            'email': 'contact_%02d@test.example.com',
        } for x in range(30)])

        self.assertEqual(len(contacts), 30)
        self.assertEqual(contacts.list_ids, self.env['mailing.list'])

        mailing = self.env['mailing.list'].create({
            'name': 'Contacts Agregator',
        })

        # create wizard with context values
        wizard_form = Form(self.env['mailing.contact.to.list'].with_context(default_contact_ids=contacts.ids))
        self.assertEqual(wizard_form.contact_ids._get_ids(), contacts.ids)

        # set mailing list and add contacts
        wizard_form.mailing_list_id = mailing
        wizard = wizard_form.save()
        action = wizard.action_add_contacts()
        self.assertEqual(contacts.list_ids, mailing)
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertTrue(action.get("params", {}).get("next"), "Should return a notification with a next action")
        subaction = action["params"]["next"]
        self.assertEqual(subaction["type"], "ir.actions.act_window_close")

        # set mailing list, add contacts and redirect to mailing view
        mailing2 = self.env['mailing.list'].create({
            'name': 'Contacts Sublimator',
        })

        wizard_form.mailing_list_id = mailing2
        wizard = wizard_form.save()
        action = wizard.action_add_contacts_and_send_mailing()
        self.assertEqual(contacts.list_ids, mailing + mailing2)
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertTrue(action.get("params", {}).get("next"), "Should return a notification with a next action")
        subaction = action["params"]["next"]
        self.assertEqual(subaction["type"], "ir.actions.act_window")
        self.assertEqual(subaction["context"]["default_contact_list_ids"], [mailing2.id])


class TestMailingListMerge(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailingListMerge, cls).setUpClass()
        cls._create_mailing_list()

        cls.mailing_list_3 = cls.env['mailing.list'].with_context(cls._test_context).create({
            'name': 'ListC',
            'contact_ids': [
                (0, 0, {'name': 'Norberto', 'email': 'norbert@example.com'}),
            ]
        })

    @users('user_marketing')
    def test_mailing_contact_create(self):
        default_list_ids = (self.mailing_list_2 | self.mailing_list_3).ids

        # simply set default list in context
        new = self.env['mailing.contact'].with_context(default_list_ids=default_list_ids).create([{
            'name': 'Contact_%d' % x,
            'email': 'contact_%d@test.example.com' % x,
        } for x in range(0, 5)])
        self.assertEqual(new.list_ids, (self.mailing_list_2 | self.mailing_list_3))

        # default list and subscriptions should be merged
        new = self.env['mailing.contact'].with_context(default_list_ids=default_list_ids).create([{
            'name': 'Contact_%d' % x,
            'email': 'contact_%d@test.example.com' % x,
            'subscription_list_ids': [(0, 0, {
                'list_id': self.mailing_list_1.id,
                'opt_out': True,
            }), (0, 0, {
                'list_id': self.mailing_list_2.id,
                'opt_out': True,
            })],
        } for x in range(0, 5)])
        self.assertEqual(new.list_ids, (self.mailing_list_1 | self.mailing_list_2 | self.mailing_list_3))
        # should correctly take subscription opt_out value
        for list_id in (self.mailing_list_1 | self.mailing_list_2).ids:
            new = new.with_context(default_list_ids=[list_id])
            self.assertTrue(all(contact.opt_out for contact in new))
        # not opt_out for new subscription without specific create values
        for list_id in self.mailing_list_3.ids:
            new = new.with_context(default_list_ids=[list_id])
            self.assertFalse(any(contact.opt_out for contact in new))

    @users('user_marketing')
    def test_mailing_list_contact_copy_in_context_of_mailing_list(self):
        MailingContact = self.env['mailing.contact']
        contact_1 = MailingContact.create({
            'name': 'Sam',
            'email': 'gamgee@shire.com',
            'subscription_list_ids': [(0, 0, {'list_id': self.mailing_list_3.id})],
        })
        # Copy the contact with default_list_ids in context, which should not raise anything
        contact_2 = contact_1.with_context(default_list_ids=self.mailing_list_3.ids).copy()
        self.assertEqual(contact_1.list_ids, contact_2.list_ids, 'Should copy the existing mailing list(s)')

    @users('user_marketing')
    def test_mailing_list_merge(self):
        # TEST CASE: Merge A,B into the list with the most recipients or mailings or the oldest
        # The mailing list A contains the same email address than 'Ybrant' in list B
        # This test ensure that the mailing lists are correctly merged and no
        # duplicates are appearing

        mailing = self.env['mailing.mailing'].create({
            'name': 'Name',
            'subject': 'Subject',
            'contact_list_ids':  self.mailing_list_1,
        })
        lists = self.mailing_list_1 + self.mailing_list_2
        result_list = lists.action_mailing_lists_merge()
        # Assert that the destination in correct
        self.assertEqual(
            result_list['res_id'], self.mailing_list_2.id,
            'The destination should be the one with the most recipients or most mailings and finally the oldest'
        )
        # Assert the number of contacts is correct
        self.assertEqual(
            len(self.mailing_list_2.contact_ids.ids), 6,
            'The number of contacts after the merge is not equal to 6')

        # Assert there's no duplicated email address
        self.assertEqual(
            len(list(set(self.mailing_list_2.mapped('contact_ids.email')))), 5,
            'Duplicates have been merged into the destination mailing list. Check %s' % (self.mailing_list_2.mapped('contact_ids.email')))
        # Assert that the archived mailing list has been replaced with the merge result
        self.assertEqual(
            mailing.contact_list_ids, self.mailing_list_2,
            'The mailing lists used in mailings were not updated after the merge'
        )
