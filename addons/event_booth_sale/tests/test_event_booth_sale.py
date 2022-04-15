# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.event_booth_sale.tests.common import TestEventBoothSaleCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests.common import tagged, users
from odoo.tools import float_compare

class TestEventBoothSale(TestEventBoothSaleCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventBoothSale, cls).setUpClass()

        cls.booth_1 = cls.env['event.booth'].create({
            'name': 'Test Booth 1',
            'booth_category_id': cls.event_booth_category_1.id,
            'event_id': cls.event_0.id,
        })

        cls.booth_2 = cls.env['event.booth'].create({
            'name': 'Test Booth 2',
            'booth_category_id': cls.event_booth_category_1.id,
            'event_id': cls.event_0.id,
        })

        cls.tax_10 = cls.env['account.tax'].sudo().create({
            'name': 'Tax 10',
            'amount': 10,
        })

        cls.pricelist = cls.env['product.pricelist'].sudo().create({
            'name': 'Test Pricelist',
        })

    @users('user_sales_salesman')
    def test_event_booth_prices_with_sale_order(self):
        self.event_booth_product.taxes_id = self.tax_10
        sale_order = self.env['sale.order'].create({
            'partner_id': self.event_customer.id,
            'pricelist_id': self.pricelist.id,
            'order_line': [
                Command.create({
                    'product_id': self.event_booth_product.id,
                    'event_id': self.event_0.id,
                    'event_booth_category_id': self.event_booth_category_1.id,
                    'event_booth_pending_ids': (self.booth_1 + self.booth_2).ids
                })
            ]
        })

        self.assertEqual(self.booth_1.price, self.event_booth_product.list_price,
                         "Booth price should be equal from product price.")
        self.assertEqual(self.event_booth_category_1.with_context(pricelist=self.pricelist.id).price_reduce_taxinc, 22.0,
                         "Booth price reduce tax should be equal to its price with 10% taxes ($20.0 + $2.0)")
        # Here we expect the price to be the sum of the booth ($40.0)
        self.assertEqual(float_compare(sale_order.amount_untaxed, 40.0, precision_rounding=0.1), 0,
                         "Untaxed amount should be the sum of the booths prices ($40.0).")
        self.assertEqual(float_compare(sale_order.amount_total, 44.0, precision_rounding=0.1), 0,
                         "Total amount should be the sum of the booths prices with 10% taxes ($40.0 + $4.0)")

        self.event_booth_category_1.write({'price': 100.0})
        sale_order.update_prices()

        self.assertNotEqual(self.booth_1.price, self.event_booth_product.list_price,
                            "Booth price should be different from product price.")
        self.assertEqual(self.event_booth_category_1.with_context(pricelist=self.pricelist.id).price_reduce_taxinc, 110.0,
                         "Booth price reduce tax should be equal to its price with 10% taxes ($100.0 + $10.0)")
        # Here we expect the price to be the sum of the booth ($200.0)
        self.assertEqual(float_compare(sale_order.amount_untaxed, 200.0, precision_rounding=0.1), 0,
                         "Untaxed amount should be the sum of the booths prices ($200.0).")
        self.assertEqual(float_compare(sale_order.amount_total, 220.0, precision_rounding=0.1), 0,
                         "Total amount should be the sum of the booths prices with 10% taxes ($200.0 + $20.0).")

        # Confirm the SO.
        sale_order.action_confirm()

@tagged('post_install', '-at_install')
class TestEventBoothSaleInvoice(TestSaleCommon, TestEventBoothSaleCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventBoothSaleInvoice, cls).setUpClass()

        cls.booth_1 = cls.env['event.booth'].create({
            'name': 'Test Booth 1',
            'booth_category_id': cls.event_booth_category_1.id,
            'event_id': cls.event_0.id,
        })

        cls.tax_10 = cls.env['account.tax'].sudo().create({
            'name': 'Tax 10',
            'amount': 10,
        })

        cls.pricelist = cls.env['product.pricelist'].sudo().create({
            'name': 'Test Pricelist',
        })

    @users('user_sales_salesman')
    def test_event_booth_with_invoice(self):
        # Add group `group_account_invoice` to user to allow to pay the invoice
        self.env.user.groups_id += self.env.ref('account.group_account_invoice')

        self.event_booth_product.taxes_id = self.tax_10
        sale_order = self.env['sale.order'].create({
            'partner_id': self.event_customer.id,
            'pricelist_id': self.pricelist.id,
            'order_line': [
                Command.create({
                    'product_id': self.event_booth_product.id,
                    'event_id': self.event_0.id,
                    'event_booth_pending_ids': (self.booth_1).ids
                })
            ]
        })
        sale_order.action_confirm()

        # Create and check that the invoice was created
        invoice = sale_order._create_invoices()
        self.assertEqual(len(sale_order.invoice_ids), 1, "Invoice not created.")

        # Confirm the invoice and check SO invoice status
        invoice.action_post()
        self.assertTrue(sale_order.invoice_status == 'invoiced', 'order is not invoiced')

        # Pay the invoice.
        journal = self.env['account.journal'].search([('type', '=', 'cash'), ('company_id', '=', sale_order.company_id.id)], limit=1)

        register_payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'journal_id': journal.id,
        })
        register_payments._create_payments()

        # Check the invoice payment state after paying the invoice
        self.assertTrue(invoice.payment_state == 'paid', 'order is not paid')
