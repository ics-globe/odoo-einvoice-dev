# -*- coding: utf-8 -*-
from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtAccount(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_pt_account.pt_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].write({
            'street': '250 Executive Park Blvd, Suite 3400',
            'city': 'Lisboa',
            'zip': '9415-343',
            'company_registry': '123456',
            'phone': '+351 11 11 11 11',
            'country_id': cls.env.ref('base.pt').id,
            'vat': 'PT123456789',
        })
        cls.company_pt = cls.company_data['company']
        cls.company_data['default_journal_sale'].restrict_mode_hash_table = True
        cls.company_data['default_journal_purchase'].restrict_mode_hash_table = True

        cls.out_invoice1 = cls.create_invoice('out_invoice', '2022-01-01')
        cls.out_invoice2 = cls.create_invoice('out_invoice', '2022-01-02')
        cls.in_invoice1 = cls.create_invoice('in_invoice', '2022-01-01')
        cls.out_invoice3 = cls.create_invoice('out_invoice', '2022-01-03')
        cls.out_refund1 = cls.create_invoice('out_refund', '2022-01-01')
        cls.in_refund1 = cls.create_invoice('in_refund', '2022-01-01')
        cls.out_invoice4 = cls.create_invoice('out_invoice', '2022-01-04')
        cls.in_refund2 = cls.create_invoice('in_refund', '2022-01-02')

    @classmethod
    def create_invoice(cls, move_type, date_str="2022-01-01"):
        invoice = cls.env['account.move'].create({
            'move_type': move_type,
            'invoice_date': fields.Date.from_string(date_str),
            'company_id': cls.company_pt.id,
            'date': date_str,
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'quantity': 1.0,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, cls.company_data['default_tax_sale'].ids)],
            })],
        })
        invoice.action_post()
        return invoice

    def test_l10n_pt_account_hash_sequence(self):
        self.assertEqual(self.out_invoice1.inalterable_hash, '0')
        self.assertEqual(self.out_invoice2.inalterable_hash, '1')
        self.assertEqual(self.out_invoice3.inalterable_hash, '2')
        self.assertEqual(self.out_invoice4.inalterable_hash, '3')
        self.assertEqual(self.in_invoice1.inalterable_hash, '0')
        self.assertEqual(self.out_refund1.inalterable_hash, '0')
        self.assertEqual(self.in_refund1.inalterable_hash, '0')
        self.assertEqual(self.in_refund2.inalterable_hash, '1')

    def test_l10n_pt_account_hash_inalterability(self):
        with self.assertRaises(UserError):
            self.out_invoice1['inalterable_hash'] = 'fake_hash'
        with self.assertRaises(UserError):
            self.out_invoice1['invoice_date'] = fields.Date.from_string('2000-01-01')
        with self.assertRaises(UserError):
            self.out_invoice1['create_date'] = fields.Datetime.now()
        with self.assertRaises(UserError):
            self.out_invoice1['amount_total'] = 9999.99

    def test_l10n_pt_account_document_no(self):
        self.assertEqual(self.out_invoice1.l10n_pt_document_no, 'out_invoice INV.2022/1')
        self.assertEqual(self.out_invoice2.l10n_pt_document_no, 'out_invoice INV.2022/2')
        self.assertEqual(self.out_invoice3.l10n_pt_document_no, 'out_invoice INV.2022/3')
        self.assertEqual(self.out_invoice4.l10n_pt_document_no, 'out_invoice INV.2022/4')
        self.assertEqual(self.in_invoice1.l10n_pt_document_no, 'in_invoice BILL.2022/01/1')
        self.assertEqual(self.out_refund1.l10n_pt_document_no, 'out_refund RINV.2022/1')
        self.assertEqual(self.in_refund1.l10n_pt_document_no, 'in_refund RBILL.2022/01/1')
        self.assertEqual(self.in_refund2.l10n_pt_document_no, 'in_refund RBILL.2022/01/2')
