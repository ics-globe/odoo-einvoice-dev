# -*- coding: utf-8 -*-
# pylint: disable=bad-whitespace
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAccountMoveInalterableHash(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_account_move_inalterable_hash(self):
        """Test that we cannot alterate a field used for the computation of the inalterable hash"""
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True
        move1 = self.init_invoice(
            move_type='out_invoice',
            invoice_date=fields.Date.from_string('2022-01-01'),
            partner=self.partner_a,
            products=self.product_a,
            post=True)

        with self.assertRaises(UserError):
            move1['inalterable_hash'] = 'fake_hash'
        with self.assertRaises(UserError):
            move1['date'] = fields.Date.from_string('2022-01-02')
        with self.assertRaises(UserError):
            move1['journal_id'] = 9999
        with self.assertRaises(UserError):
            move1['company_id'] = 9999

        with self.assertRaises(UserError):
            move1.line_ids[0]['debit'] += 10
        with self.assertRaises(UserError):
            move1.line_ids[0]['credit'] += 10
        with self.assertRaises(UserError):
            move1.line_ids[0]['account_id'] = 9999
        with self.assertRaises(UserError):
            move1.line_ids[0]['partner_id'] = 9999
