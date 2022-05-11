# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from unittest.mock import patch

from odoo import fields
from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TestStockValuation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.partner_id = cls.env['res.partner'].create({
            'name': 'Wood Corner Partner',
            'company_id': cls.env.user.company_id.id,
        })
        cls.product1 = cls.env['product.product'].create({
            'name': 'Large Desk',
            'standard_price': 1299.0,
            'list_price': 1799.0,
            'type': 'product',
        })
        Account = cls.env['account.account']
        cls.stock_input_account = Account.create({
            'name': 'Stock Input',
            'code': 'StockIn',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
        })
        cls.stock_output_account = Account.create({
            'name': 'Stock Output',
            'code': 'StockOut',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
        })
        cls.stock_valuation_account = Account.create({
            'name': 'Stock Valuation',
            'code': 'Stock Valuation',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
        })
        cls.stock_journal = cls.env['account.journal'].create({
            'name': 'Stock Journal',
            'code': 'STJTEST',
            'type': 'general',
        })
        cls.product1.categ_id.write({
            'property_stock_account_input_categ_id': cls.stock_input_account.id,
            'property_stock_account_output_categ_id': cls.stock_output_account.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
            'property_stock_journal': cls.stock_journal.id,
        })

    def check_svl_values(self, svl, quantity=0, unit_cost=0, value=0, product=False, linked_to=False):
        err_msg = "Stock Valuation Layer\'s {field} should be {expected}, but is {value} instead."
        self.assertEqual(svl.quantity, quantity,
                         err_msg.format(field="quantity", expected=quantity, value=svl.quantity))
        self.assertEqual(svl.unit_cost, unit_cost,
                         err_msg.format(field="unit cost", expected=unit_cost, value=svl.unit_cost))
        self.assertEqual(svl.value, value,
                         err_msg.format(field="value", expected=value, value=svl.value))
        if linked_to:
            self.assertEqual(
                svl.stock_valuation_layer_id.id, linked_to.id,
                f'SVL "{svl.description}" (id {svl.id}) should be linked to "{linked_to.description}"\
                (id {linked_to.id}): it is linked to {svl.stock_valuation_layer_id.id} instead')
        else:
            self.assertFalse(
                svl.stock_valuation_layer_id.id,
                f'SVL "{svl.description}" (id {svl.id}) should not be linked to any other SVL')

        if product:
            self.assertEqual(
                svl.product_id, product,
                err_msg.format(field="product", expected=product.name, value=svl.product_id.name))

    def test_change_unit_cost_average_1(self):
        """ Confirm a purchase order and create the associated receipt, change the unit cost of the
        purchase order before validating the receipt, the value of the received goods should be set
        according to the last unit cost.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_ids[0]

        # the unit price of the purchase order line is copied to the in move
        self.assertEqual(move1.price_unit, 100)

        # update the unit price on the purchase order line
        po1.order_line.price_unit = 200

        # the unit price on the stock move is not directly updated
        self.assertEqual(move1.price_unit, 100)

        # validate the receipt
        res_dict = picking1.button_validate()
        wizard = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict['context'])).save()
        wizard.process()

        # the unit price of the valuationlayer used the latest value
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 200)

        self.assertEqual(self.product1.value_svl, 2000)

    def test_standard_price_change_1(self):
        """ Confirm a purchase order and create the associated receipt, change the unit cost of the
        purchase order and the standard price of the product before validating the receipt, the
        value of the received goods should be set according to the last standard price.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'

        # set a standard price
        self.product1.product_tmpl_id.standard_price = 10

        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 11.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_ids[0]

        # the move's unit price reflects the purchase order line's cost even if it's useless when
        # the product's cost method is standard
        self.assertEqual(move1.price_unit, 11)

        # set a new standard price
        self.product1.product_tmpl_id.standard_price = 12

        # the unit price on the stock move is not directly updated
        self.assertEqual(move1.price_unit, 11)

        # validate the receipt
        res_dict = picking1.button_validate()
        wizard = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict['context'])).save()
        wizard.process()

        # the unit price of the valuation layer used the latest value
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 12)

        self.assertEqual(self.product1.value_svl, 120)

    def test_extra_move_fifo_1(self):
        """ Check that the extra move when over processing a receipt is correctly merged back in
        the original move.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_ids[0]
        move1.quantity_done = 15
        picking1.button_validate()

        # there should be only one move
        self.assertEqual(len(picking1.move_ids), 1)
        self.assertEqual(move1.price_unit, 100)
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 100)
        self.assertEqual(move1.product_qty, 15)
        self.assertEqual(self.product1.value_svl, 1500)

    def test_backorder_fifo_1(self):
        """ Check that the backordered move when under processing a receipt correctly keep the
        price unit of the original move.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_ids[0]
        move1.quantity_done = 5
        res_dict = picking1.button_validate()
        self.assertEqual(res_dict['res_model'], 'stock.backorder.confirmation')
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id')).with_context(res_dict['context'])
        wizard.process()

        self.assertEqual(len(picking1.move_ids), 1)
        self.assertEqual(move1.price_unit, 100)
        self.assertEqual(move1.product_qty, 5)

        picking2 = po1.picking_ids.filtered(lambda p: p.backorder_id)
        move2 = picking2.move_ids[0]
        self.assertEqual(len(picking2.move_ids), 1)
        self.assertEqual(move2.price_unit, 100)
        self.assertEqual(move2.product_qty, 5)

    def test_anglosaxon_valuation_price_unit_diff_receipt_before_bill_01(self):
        """ Receives a product, increases the price into the bill, then receives
        the same product a second time with another price.
        PO: 5 units at $5.0
        Inv: price unit: $10.0
        Increase PO line quantity at 7
        Inv: price unit: $25.0
        Checks the Stock Valuation Layers are correctly created.
        """
        StockValuationLayer = self.env['stock.valuation.layer']
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        # Creates a PO with the first PO line (5 units at $5.0).
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 5
            po_line.price_unit = 5.0
        order = po_form.save()
        order.button_confirm()

        # Receives the goods.
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity_done = 5
        receipt.button_validate()

        # Creates an invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 10.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 2)
        svl_1 = svl[0]  # SVL for the receipt of product1.
        svl_2 = svl[1]  # SVL for the price difference correction.
        self.check_svl_values(svl_1, quantity=5.0, unit_cost=5.0, value=25.0)
        self.check_svl_values(svl_2, quantity=0.0, unit_cost=0.0, value=25.0, linked_to=svl_1)
        self.assertEqual(sum(svl.mapped('value')), 50.0)

        # # Checks if something was posted in the price difference account
        # price_diff_aml = self.env['account.move.line'].search([('account_id', '=', self.price_diff_account.id)])
        # self.assertEqual(len(price_diff_aml), 0, "No line should have been generated in the price difference account.")

        # Checks what was posted in stock input account
        input_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)])
        self.assertEqual(
            len(input_aml), 3,
            "Three lines should have been generated in stock input account:"
            "\n\t- one when receiving the product"
            "\n\t- one when making the invoice"
            "\n\t- one for the difference price"
        )
        self.assertEqual(sum(input_aml.mapped('debit')), 50)
        self.assertEqual(sum(input_aml.mapped('credit')), 50)

        # Increases the PO line quantity (that will create a second receipt for the extra qty).
        po_form = Form(order)
        with po_form.order_line.edit(0) as po_line:
            po_line.product_qty = 7
        order = po_form.save()
        order.button_confirm()

        # Receives the goods.
        receipt = order.picking_ids.filtered(lambda p: p.state == 'assigned')[0]
        receipt.move_ids.quantity_done = 2
        receipt.button_validate()

        # Creates a second invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 25.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Checks stock valuation layers.
        svl = self.env['stock.valuation.layer'].search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 4)
        svl_3 = svl[2]  # SVL for the second receipt.
        svl_4 = svl[3]  # SVL for the price difference correction.
        self.check_svl_values(svl_3, quantity=2.0, unit_cost=5.0, value=10.0)
        self.check_svl_values(svl_4, value=40.0, linked_to=svl_3)
        self.assertEqual(sum(svl.mapped('value')), 100.0)

    def test_anglosaxon_valuation_price_unit_diff_receipt_before_bill_02(self):
        """ Purchases 4 units at $5, receives them then invoices 5 units at $10:
        -> Should correctly creates the SVL for the price's difference.
        Then, increases the purchase qty to 5 and receives the extra:
        -> The SVL should get the price from the extra invoiced qty instead of the purchase's one.
        """
        StockValuationLayer = self.env['stock.valuation.layer']
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        # Creates a PO with the first PO line (4 units at $5.0).
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 4
            po_line.price_unit = 5.0
        order = po_form.save()
        order.button_confirm()

        # Receives the goods.
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity_done = 4
        receipt.button_validate()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 1)
        svl_1 = svl[0]  # SVL for the receipt of product1.
        self.check_svl_values(svl_1, quantity=4.0, unit_cost=5.0, value=20.0)

        # Creates an invoice and increases the price AND the quantity.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 5.0
            line_form.price_unit = 10.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 2)
        svl_2 = svl[1]  # SVL for the price difference correction.
        self.check_svl_values(svl_2, quantity=0.0, unit_cost=0.0, value=20.0, linked_to=svl_1)
        self.assertEqual(sum(svl.mapped('value')), 40.0)

        # Edits the PO line.
        po_form = Form(order)
        with po_form.order_line.edit(0) as po_line:
            po_line.product_qty = 5
        order = po_form.save()
        order.button_confirm()

        # Receives the goods (second line).
        receipt = order.picking_ids.filtered(lambda p: p.state == 'assigned')[0]
        receipt.move_ids.quantity_done = 1
        receipt.button_validate()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 3)
        svl_3 = svl[2]  # SVL for the second receipt.
        self.check_svl_values(svl_3, quantity=1.0, unit_cost=10.0, value=10.0)
        self.assertEqual(sum(svl.mapped('value')), 50.0)

    def test_anglosaxon_valuation_price_unit_diff_receipt_before_bill_03(self):
        """ Receives a product, increases the price into the bill, then receive
        the same product a second time with another price.
        PO: 4 units at $5.0, receipt.
        Inv: 5 units at $10.0
        PO: increase line qty. to 6, receipt.
        Inv: 1 unit at $10.0
        Checks the Stock Valuation Layers are correctly created.
        """
        StockValuationLayer = self.env['stock.valuation.layer']
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        # Creates a PO with the first PO line (4 units at $5.0).
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 4
            po_line.price_unit = 5.0
        order = po_form.save()
        order.button_confirm()

        # Receives the goods.
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity_done = 4
        receipt.button_validate()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 1)
        svl_1 = svl[0]  # SVL for the product1.
        self.check_svl_values(svl_1, quantity=4.0, unit_cost=5.0, value=20.0)

        # Creates an invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 5.0
            line_form.price_unit = 10.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 2)
        svl_2 = svl[1]  # SVL for the price difference correction.
        self.check_svl_values(svl_2, quantity=0.0, unit_cost=0.0, value=20.0, linked_to=svl_1)
        self.assertEqual(sum(svl.mapped('value')), 40.0)

        # Edits the PO line.
        po_form = Form(order)
        with po_form.order_line.edit(0) as po_line:
            po_line.product_qty = 6
        order = po_form.save()
        order.button_confirm()

        # Receives the goods (second line).
        receipt = order.picking_ids.filtered(lambda p: p.state == 'assigned')[0]
        receipt.move_ids.quantity_done = 2
        receipt.button_validate()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 4)
        svl_3 = svl[2]  # SVL with the invoice price (extra qty already proceed in the invoice).
        svl_4 = svl[3]  # SVL with the PO price (extra qty not present in the invoice).
        self.check_svl_values(svl_3, quantity=1.0, unit_cost=10.0, value=10.0)
        self.check_svl_values(svl_4, quantity=1.0, unit_cost=5.0, value=5.0)
        self.assertEqual(sum(svl.mapped('value')), 55.0)

        # Creates a second invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 1
            line_form.price_unit = 10.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 5)
        svl_5 = svl[4]  # SVL for the price difference correction.
        self.check_svl_values(svl_5, quantity=0.0, unit_cost=0.0, value=5.0, linked_to=svl_4)
        self.assertEqual(sum(svl.mapped('value')), 60.0)

    def test_anglosaxon_valuation_price_unit_diff_bill_before_receipt_01(self):
        """ Creates an invoice, then receives the product.
        PO: 5 units at $5.0
        Inv: price unit: $10.0
        PO: adds 2 units at $20.0
        Inv: price unit: $25.0
        Checks the Stock Valuation Layers are correctly created.
        """
        StockValuationLayer = self.env['stock.valuation.layer']
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        # Creates a PO with the first PO line (5 units at $5.0).
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 5
            po_line.price_unit = 5.0
        order = po_form.save()
        order.button_confirm()

        # Creates an invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 5
            line_form.price_unit = 10.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Receives the goods.
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity_done = 5
        receipt.button_validate()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 1)
        self.check_svl_values(svl, quantity=5.0, unit_cost=10.0, value=50.0)

        # Adds a second PO line.
        po_form = Form(order)
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 2
            po_line.price_unit = 20.0
        order = po_form.save()
        order.button_confirm()

        # Creates a second invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(1) as line_form:
            line_form.quantity = 2
            line_form.price_unit = 25.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Receives the goods (for the second PO line).
        receipt = order.picking_ids.filtered(lambda p: p.state == 'assigned')[0]
        receipt.move_ids.quantity_done = 2
        receipt.button_validate()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 2)
        svl_2 = svl[1]
        self.check_svl_values(svl_2, quantity=2.0, unit_cost=25.0, value=50.0)
        self.assertEqual(sum(svl.mapped('value')), 100.0)

    def test_anglosaxon_valuation_price_unit_diff_bill_before_receipt_02(self):
        """ Creates an invoice, then receives the product.
        PO: 5 units at $5.0
        Inv: price unit: 5 at $10.0
        Receipt only 4, no backorder.
        PO: increase quantity at 7 units
        Inv: price unit: 2 at $25.0
        Receipt 3 unit.
        Checks the Stock Valuation Layers are correctly created.
        """
        StockValuationLayer = self.env['stock.valuation.layer']
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        # Creates a PO with the first PO line (5 units at $5.0).
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 5
            po_line.price_unit = 5.0
        order = po_form.save()
        order.button_confirm()

        # Creates an invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 5
            line_form.price_unit = 10.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Receives partially the goods.
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity_done = 4
        # Handles the backorder wizard as the receipt isn't complete.
        wizard = receipt.button_validate()
        wizard_form = Form(self.env['stock.backorder.confirmation'].with_context(wizard['context']))
        wizard = wizard_form.save()
        wizard.process_cancel_backorder()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 1)
        self.check_svl_values(svl, quantity=4.0, unit_cost=10.0, value=40.0)

        # Edits the PO line and increases the quantity.
        po_form = Form(order)
        with po_form.order_line.edit(0) as po_line:
            po_line.product_qty = 7
        order = po_form.save()

        # Creates a second invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 2
            line_form.price_unit = 25.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Receives the goods (for the added quantity).
        receipt = order.picking_ids.filtered(lambda p: p.state == 'assigned')[0]
        receipt.move_ids.quantity_done = 3
        receipt.button_validate()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 3)
        svl_2, svl_3 = svl[1:].sorted(lambda layer: layer.quantity)
        # The second receipt must have created two SVL because the 3 received
        # quantities refer to two invoices with different prices.
        self.check_svl_values(svl_2, quantity=1.0, unit_cost=10.0, value=10.0)
        self.check_svl_values(svl_3, quantity=2.0, unit_cost=25.0, value=50.0)
        self.assertEqual(sum(svl.mapped('value')), 100.0)

    def test_anglosaxon_valuation_price_unit_diff_bill_before_receipt_03_uom(self):
        """ Creates a purchase for 2 dozens at $120 and invoices them at $180.
        Then, receives the 24 units and checks the SVL is correctly created.
        """
        StockValuationLayer = self.env['stock.valuation.layer']
        self.env.user.write({'groups_id': [(4, self.env.ref('uom.group_uom').id)]})
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'
        uom_dozen = self.env.ref('uom.product_uom_dozen')

        # Creates a PO with the first PO line (2 dozen at $5.0).
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_uom = uom_dozen
            po_line.product_qty = 2
            po_line.price_unit = 120.0
        order = po_form.save()
        order.button_confirm()

        # Creates an invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 2
            line_form.price_unit = 180.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()
        self.assertEqual(invoice.invoice_line_ids.product_uom_id.id, uom_dozen.id)

        # Receives the goods.
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity_done = 24
        receipt.button_validate()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 1)
        self.check_svl_values(svl, quantity=24.0, unit_cost=15, value=360.0)
        #  Checks the waiting quantity on the invoice line was correclty decreased.
        self.assertEqual(invoice.invoice_line_ids.qty_waiting_for_receipt, 0)

    def test_anglosaxon_valuation_price_unit_diff_mixed_order_01(self):
        """ For one purchase order, creates an invoice then receives product.
        Then, updates the po line quantity, receives the product and creates a another invoices.
        PO: 5 units at $5.0
        Inv: price unit: 5 at $10.0
        Receipt 5 units.
        PO: increase quantity at 10 units
        Receipt 5 units.
        Inv: price unit: 5 at $25.0
        Checks the Stock Valuation Layers are correctly created.
        """
        StockValuationLayer = self.env['stock.valuation.layer']
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        # Creates a PO with the first PO line (5 units at $5.0).
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 5
            po_line.price_unit = 5.0
        order = po_form.save()
        order.button_confirm()

        # Creates an invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 5
            line_form.price_unit = 10.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Receives the goods.
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity_done = 5
        receipt.button_validate()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 1)
        self.check_svl_values(svl, quantity=5.0, unit_cost=10.0, value=50.0)

        # Edits the PO line and increases the quantity.
        po_form = Form(order)
        with po_form.order_line.edit(0) as po_line:
            po_line.product_qty = 10
        order = po_form.save()

        # Receives the goods (for the added quantity).
        receipt = order.picking_ids.filtered(lambda p: p.state == 'assigned')[0]
        receipt.move_ids.quantity_done = 5
        receipt.button_validate()

        # Creates a second invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 5
            line_form.price_unit = 25.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 3)
        svl_2 = svl[1]  # SVL created by the second receipt.
        svl_3 = svl[2]  # SVL for the price difference between the 2nd receipt and the 2nd invoice.
        self.check_svl_values(svl_2, quantity=5.0, unit_cost=5.0, value=25.0)
        self.check_svl_values(svl_3, quantity=0.0, unit_cost=0.0, value=100.0, linked_to=svl_2)
        self.assertEqual(sum(svl.mapped('value')), 175.0)

    def test_anglosaxon_valuation_price_unit_diff_mixed_order_02(self):
        """ For one purchase order, receives product then creates an invoice.
        Then, updates the po line quantity, creates an another invoice and receives the product.
        PO: 5 units at $5.0
        Receipt 5 units.
        Inv: price unit: 5 at $10.0
        PO: increase quantity at 10 units
        Inv: price unit: 5 at $25.0
        Receipt 5 units.
        Checks the Stock Valuation Layers are correctly created.
        """
        StockValuationLayer = self.env['stock.valuation.layer']
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        # Creates a PO with the first PO line (5 units at $5.0).
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 5
            po_line.price_unit = 5.0
        order = po_form.save()
        order.button_confirm()

        # Receives the goods.
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity_done = 5
        receipt.button_validate()

        # Creates an invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 5
            line_form.price_unit = 10.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 2)
        svl_1 = svl[0]  # SVL created by the receipt.
        svl_2 = svl[1]  # SVL for the price difference between the receipt and the invoice.
        self.check_svl_values(svl_1, quantity=5.0, unit_cost=5.0, value=25.0)
        self.check_svl_values(svl_2, quantity=0, unit_cost=0, value=25.0, linked_to=svl_1)
        self.assertEqual(sum(svl.mapped('value')), 50.0)

        # Edits the PO line and increases the quantity.
        po_form = Form(order)
        with po_form.order_line.edit(0) as po_line:
            po_line.product_qty = 10
        order = po_form.save()

        # Creates a second invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 5
            line_form.price_unit = 25.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Receives the goods (for the added quantity).
        receipt = order.picking_ids.filtered(lambda p: p.state == 'assigned')[0]
        receipt.move_ids.quantity_done = 5
        receipt.button_validate()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(svl), 3)
        svl_3 = svl[2]
        self.check_svl_values(svl_3, quantity=5.0, unit_cost=25.0, value=125.0)
        self.assertEqual(sum(svl.mapped('value')), 175.0)

    def test_anglosaxon_valuation_price_unit_diff_multiple_invoice_lines_01(self):
        """ Creates a purchase order for 6 products then creates an invoice with two lines:
        PO line: 6 units at $5.0
        Inv line #1: 4 units at $7.0
        Inv line #2: 2 units at $10.0

        Then receives the product and checks two SVL were created with the right values.
        """
        StockValuationLayer = self.env['stock.valuation.layer']
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        # Creates a PO with the first PO line (6 units at $5.0).
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 6
            po_line.price_unit = 5.0
        order = po_form.save()
        order.button_confirm()

        # Creates an invoice and increases the price (two different lines with different prices).
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 4
            line_form.price_unit = 7.0
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 2
            line_form.price_unit = 10.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Receives the goods.
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity_done = 6
        receipt.button_validate()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', '=', self.product1.id)], order='quantity DESC')
        self.assertEqual(len(svl), 2)
        svl_1 = svl[0]  # SVL with price unit from the first invoice line.
        svl_2 = svl[1]  # SVL with price unit from the second invoice line.
        self.check_svl_values(svl_1, quantity=4.0, unit_cost=7.0, value=28.0)
        self.check_svl_values(svl_2, quantity=2.0, unit_cost=10.0, value=20.0)
        self.assertEqual(sum(svl.mapped('value')), 48.0)

    def test_anglosaxon_valuation_price_unit_diff_multiple_products_01(self):
        """ Creates a purchase order for two products (AVCO and FIFO):
        PO line #1: 5 FIFO at $5.0
        PO line #2: 5 AVCO at $7.0

        First, receives only 4 FIFO and creates an invoice:
        Invoice line #1: 6 FIFO at $10.0
        Invoice line #2: 5 AVCO at $14.0

        Updates the purchase order quantities (6 FIFO and 10 AVCO), receives the remaining qty and
        Invoice line: 5 AVCO at $12.0

        Finally, checks the Stock Valuation Layers were correctly created.
        """
        StockValuationLayer = self.env['stock.valuation.layer']
        self.env.company.anglo_saxon_accounting = True
        product_fifo = self.product1
        product_fifo.categ_id.property_cost_method = 'fifo'
        product_fifo.categ_id.property_valuation = 'real_time'
        product_avco = self.env['product.product'].create({
            'name': 'AVCO Product',
            'standard_price': 100.0,
            'list_price': 120.0,
            'type': 'product',
        })
        product_avco.categ_id.property_cost_method = 'average'
        product_avco.categ_id.property_valuation = 'real_time'

        # Creates a PO 5 product_fifo at $5.0 and 5 product_avco at $7.0.
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = product_fifo
            po_line.product_qty = 5
            po_line.price_unit = 5.0
        with po_form.order_line.new() as po_line:
            po_line.product_id = product_avco
            po_line.product_qty = 5
            po_line.price_unit = 7.0
        order = po_form.save()
        order.button_confirm()

        # Receives 4 product_fifo.
        receipt = order.picking_ids[0]
        receipt.move_ids[0].quantity_done = 4
        # Handles the backorder wizard as the receipt isn't complete.
        wizard = receipt.button_validate()
        wizard_form = Form(self.env['stock.backorder.confirmation'].with_context(wizard['context']))
        wizard = wizard_form.save()
        wizard.process_cancel_backorder()

        # Creates an invoice for 6 product_fifo at $10 and 5 product_avco at $14.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_fifo_product:
            line_fifo_product.quantity = 6
            line_fifo_product.price_unit = 10.0
        with invoice_form.invoice_line_ids.edit(1) as line_avco_product:
            line_avco_product.quantity = 5
            line_avco_product.price_unit = 14.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', 'in', [product_fifo.id, product_avco.id])])
        self.assertEqual(len(svl), 2)
        svl_1 = svl[0]  # SVL created by the receipt.
        svl_2 = svl[1]  # SVL for the price difference between the receipt and the invoice.
        self.check_svl_values(svl_1, product=product_fifo, quantity=4.0, unit_cost=5.0, value=20.0)
        self.check_svl_values(svl_2, product=product_fifo, value=20.0, linked_to=svl_1)
        self.assertEqual(sum(svl.mapped('value')), 40.0)

        # Edits the PO line and increases product_fifo qty to 6 and product_avco qty to 10.
        po_form = Form(order)
        with po_form.order_line.edit(0) as po_line_product_fifo:
            po_line_product_fifo.product_qty = 6
        with po_form.order_line.edit(1) as po_line_product_avco:
            po_line_product_avco.product_qty = 10
        order = po_form.save()

        # Processes the second receipt for 2 product_fifo and 10 product_avco.
        receipt = order.picking_ids[0]
        receipt.move_ids[0].quantity_done = 2
        receipt.move_ids[1].quantity_done = 10
        receipt.button_validate()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', 'in', [product_fifo.id, product_avco.id])])
        self.assertEqual(len(svl), 5)
        svl_3 = svl[2]  # SVL for 2 product_fifo, unit cost from the invoice.
        svl_4 = svl[3]  # SVL for 5 product_avco, unit cost from the invoice.
        svl_5 = svl[4]  # SVL for 5 product_avco, unit cost from the PO line.
        self.check_svl_values(svl_3, product=product_fifo, quantity=2, unit_cost=10.0, value=20.0)
        self.check_svl_values(svl_4, product=product_avco, quantity=5, unit_cost=14.0, value=70.0)
        self.check_svl_values(svl_5, product=product_avco, quantity=5, unit_cost=7.0, value=35.0)
        self.assertEqual(sum(svl.mapped('value')), 165.0)

        # Creates a second invoice and increases the price.
        invoice_form = Form(self.env['account.move'].with_context(default_purchase_id=order.id, default_move_type='in_invoice'))
        with invoice_form.invoice_line_ids.edit(1) as line_form:
            line_form.quantity = 5
            line_form.price_unit = 12.0
        invoice_form.invoice_date = fields.Date.today()
        invoice = invoice_form.save()
        invoice.action_post()

        # Checks stock valuation layers.
        svl = StockValuationLayer.search([('product_id', 'in', [product_fifo.id, product_avco.id])])
        self.assertEqual(len(svl), 6)
        svl_6 = svl[5]  # SVL for the price difference between the receipt and the second invoice.
        self.check_svl_values(svl_6, product=product_avco, value=25.0, linked_to=svl_5)
        self.assertEqual(sum(svl.mapped('value')), 190.0)


@tagged('post_install', '-at_install')
class TestStockValuationWithCOA(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.partner_id = cls.env['res.partner'].create({'name': 'Wood Corner Partner'})
        cls.product1 = cls.env['product.product'].create({'name': 'Large Desk'})

        cls.cat = cls.env['product.category'].create({
            'name': 'cat',
        })
        cls.product1 = cls.env['product.product'].create({
            'name': 'product1',
            'type': 'product',
            'categ_id': cls.cat.id,
        })
        cls.product1_copy = cls.env['product.product'].create({
            'name': 'product1',
            'type': 'product',
            'categ_id': cls.cat.id,
        })

        Account = cls.env['account.account']
        cls.usd_currency = cls.env.ref('base.USD')
        cls.eur_currency = cls.env.ref('base.EUR')
        cls.usd_currency.active = True
        cls.eur_currency.active = True

        cls.stock_input_account = Account.create({
            'name': 'Stock Input',
            'code': 'StockIn',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
        })
        cls.stock_output_account = Account.create({
            'name': 'Stock Output',
            'code': 'StockOut',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
        })
        cls.stock_valuation_account = Account.create({
            'name': 'Stock Valuation',
            'code': 'Stock Valuation',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
        })
        cls.price_diff_account = Account.create({
            'name': 'price diff account',
            'code': 'price diff account',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
        })
        cls.stock_journal = cls.env['account.journal'].create({
            'name': 'Stock Journal',
            'code': 'STJTEST',
            'type': 'general',
        })
        cls.product1.categ_id.write({
            'property_stock_account_input_categ_id': cls.stock_input_account.id,
            'property_stock_account_output_categ_id': cls.stock_output_account.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
            'property_stock_journal': cls.stock_journal.id,
        })

    def test_change_currency_rate_average_1(self):
        """ Confirm a purchase order in another currency and create the associated receipt, change
        the currency rate, validate the receipt and then check that the value of the received goods
        is set according to the last currency rate.
        """
        self.env['res.currency.rate'].search([]).unlink()
        usd_currency = self.env.ref('base.USD')
        self.env.company.currency_id = usd_currency.id

        eur_currency = self.env.ref('base.EUR')

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'

        # default currency is USD, create a purchase order in EUR
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'currency_id': eur_currency.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_ids[0]

        # convert the price unit in the company currency
        price_unit_usd = po1.currency_id._convert(
            po1.order_line.price_unit, po1.company_id.currency_id,
            self.env.company, fields.Date.today(), round=False)

        # the unit price of the move is the unit price of the purchase order line converted in
        # the company's currency
        self.assertAlmostEqual(move1.price_unit, price_unit_usd, places=2)

        # change the rate of the currency
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y-%m-%d'),
            'rate': 2.0,
            'currency_id': eur_currency.id,
            'company_id': po1.company_id.id,
        })
        eur_currency._compute_current_rate()
        price_unit_usd_new_rate = po1.currency_id._convert(
            po1.order_line.price_unit, po1.company_id.currency_id,
            self.env.company, fields.Date.today(), round=False)

        # the new price_unit is lower than th initial because of the rate's change
        self.assertLess(price_unit_usd_new_rate, price_unit_usd)

        # the unit price on the stock move is not directly updated
        self.assertAlmostEqual(move1.price_unit, price_unit_usd, places=2)

        # validate the receipt
        res_dict = picking1.button_validate()
        wizard = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict['context'])).save()
        wizard.process()

        # the unit price of the valuation layer used the latest value
        self.assertAlmostEqual(move1.stock_valuation_layer_ids.unit_cost, price_unit_usd_new_rate)

        self.assertAlmostEqual(self.product1.value_svl, price_unit_usd_new_rate * 10, delta=0.1)

    def test_fifo_anglosaxon_return(self):
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        # Receive 10@10 ; create the vendor bill
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 10.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()
        receipt_po1 = po1.picking_ids[0]
        receipt_po1.move_ids.quantity_done = 10
        receipt_po1.button_validate()

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.invoice_date = move_form.date
        move_form.partner_id = self.partner_id
        move_form.purchase_id = po1
        invoice_po1 = move_form.save()
        invoice_po1.action_post()

        # Receive 10@20 ; create the vendor bill
        po2 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 20.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po2.button_confirm()
        receipt_po2 = po2.picking_ids[0]
        receipt_po2.move_ids.quantity_done = 10
        receipt_po2.button_validate()

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.invoice_date = move_form.date
        move_form.partner_id = self.partner_id
        move_form.purchase_id = po2
        invoice_po2 = move_form.save()
        invoice_po2.action_post()

        # valuation of product1 should be 300
        self.assertEqual(self.product1.value_svl, 300)

        # return the second po
        stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(
            active_ids=receipt_po2.ids, active_id=receipt_po2.ids[0], active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 10
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_ids[0].move_line_ids[0].qty_done = 10
        return_pick.button_validate()

        # valuation of product1 should be 200 as the first items will be sent out
        self.assertEqual(self.product1.value_svl, 200)

        # create a credit note for po2
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_refund'))
        move_form.invoice_date = move_form.date
        move_form.partner_id = self.partner_id
        move_form.purchase_id = po2
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 10
        creditnote_po2 = move_form.save()
        creditnote_po2.action_post()

        # check the anglo saxon entries
        price_diff_entry = self.env['account.move.line'].search([
            ('account_id', '=', self.stock_valuation_account.id),
            ('move_id', '=', creditnote_po2.id)])
        self.assertEqual(price_diff_entry.credit, 100)

    def test_anglosaxon_valuation(self):
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        # Create PO
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        order = po_form.save()
        order.button_confirm()

        # Receive the goods
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity_done = 1
        receipt.button_validate()

        stock_valuation_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_valuation_account.id)])
        receipt_aml = stock_valuation_aml[0]
        self.assertEqual(len(stock_valuation_aml), 1, "For now, only one line for the stock valuation account")
        self.assertAlmostEqual(receipt_aml.debit, 10, "Should be equal to the PO line unit price (10)")

        # Create an invoice with a different price
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.invoice_date = move_form.date
        move_form.partner_id = order.partner_id
        move_form.purchase_id = order
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 15.0
        invoice = move_form.save()
        invoice.action_post()

        # Check what was posted in the price difference account
        stock_valuation_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_valuation_account.id)])
        price_diff_aml = stock_valuation_aml - receipt_aml
        self.assertEqual(len(stock_valuation_aml), 2, "A second line should have been generated for the price difference.")
        self.assertAlmostEqual(price_diff_aml.debit, 5, "Price difference should be equal to 5 (15-10)")
        self.assertAlmostEqual(
            sum(stock_valuation_aml.mapped('debit')), 15,
            "Total debit value on stock valuation account should be equal to the invoiced price of the product.")

        # Check what was posted in stock input account
        input_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)])
        self.assertEqual(len(input_aml), 3, "Only three lines should have been generated in stock input account: one when receiving the product, one when making the invoice.")
        invoice_amls = input_aml.filtered(lambda l: l.move_id == invoice)
        picking_aml = input_aml - invoice_amls
        self.assertAlmostEqual(sum(invoice_amls.mapped('debit')), 15, "Total debit value on stock input account should be equal to the original PO price of the product.")
        self.assertAlmostEqual(sum(invoice_amls.mapped('credit')), 5, "Total debit value on stock input account should be equal to the original PO price of the product.")
        self.assertAlmostEqual(sum(picking_aml.mapped('credit')), 10, "Total credit value on stock input account should be equal to the original PO price of the product.")

    def test_valuation_from_increasing_tax(self):
        """ Check that a tax without account will increment the stock value.
        """

        tax_with_no_account = self.env['account.tax'].create({
            'name': "Tax with no account",
            'amount_type': 'fixed',
            'amount': 5,
            'sequence': 8,
        })

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        # Receive 10@10 ; create the vendor bill
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'taxes_id': [(4, tax_with_no_account.id)],
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 10.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()
        receipt_po1 = po1.picking_ids[0]
        receipt_po1.move_ids.quantity_done = 10
        receipt_po1.button_validate()

        # valuation of product1 should be 15 as the tax with no account set
        # has gone to the stock account, and must be reflected in inventory valuation
        self.assertEqual(self.product1.value_svl, 150)

    def test_average_realtime_anglo_saxon_valuation_multicurrency_same_date(self):
        """
        The PO and invoice are in the same foreign currency.
        The PO is invoiced on the same date as its creation.
        This shouldn't create a price difference entry.
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency

        date_po = '2019-01-01'

        # SetUp product
        self.product1.product_tmpl_id.cost_method = 'average'
        self.product1.product_tmpl_id.valuation = 'real_time'
        self.product1.product_tmpl_id.purchase_method = 'purchase'

        # SetUp currency and rates
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", (self.usd_currency.id, company.id))
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.0,
            'currency_id': self.usd_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.5,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        # Proceed
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': date_po,
                }),
            ],
        })
        po.button_confirm()

        inv = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
            'invoice_date': date_po,
            'date': date_po,
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Test',
                'price_unit': 100.0,
                'product_id': self.product1.id,
                'purchase_line_id': po.order_line.id,
                'quantity': 1.0,
                'account_id': self.stock_input_account.id,
            })]
        })

        inv.action_post()

        move_lines = inv.line_ids
        self.assertEqual(len(move_lines), 2)

        payable_line = move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')

        self.assertEqual(payable_line.amount_currency, -100.0)
        self.assertAlmostEqual(payable_line.balance, -66.67)

        stock_line = move_lines.filtered(lambda l: l.account_id == self.stock_input_account)
        self.assertEqual(stock_line.amount_currency, 100.0)
        self.assertAlmostEqual(stock_line.balance, 66.67)

    def test_realtime_anglo_saxon_valuation_multicurrency_different_dates(self):
        """
        The PO and invoice are in the same foreign currency.
        The PO is invoiced at a later date than its creation.
        This should create a price difference entry for standard cost method
        Not for average cost method though, since the PO and invoice have the same currency
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        date_po = '2019-01-01'
        date_invoice = '2019-01-16'

        # SetUp product Average
        self.product1.product_tmpl_id.purchase_method = 'purchase'

        # SetUp product Standard
        # should have bought at 60 USD
        # actually invoiced at 70 EUR > 35 USD
        product_categ_standard = self.cat.copy({
            'property_cost_method': 'standard',
            'property_stock_account_input_categ_id': self.stock_input_account.id,
            'property_stock_account_output_categ_id': self.stock_output_account.id,
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
            'property_stock_journal': self.stock_journal.id,
        })
        product_standard = self.product1_copy
        product_standard.write({
            'categ_id': product_categ_standard.id,
            'name': 'Standard Val',
            'standard_price': 60,
        })

        # SetUp currency and rates
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", (self.usd_currency.id, company.id))
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.0,
            'currency_id': self.usd_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.5,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_invoice,
            'rate': 2,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        # To allow testing validation of PO
        def _today(*args, **kwargs):
            return date_po
        patchers = [
            patch('odoo.fields.Date.context_today', _today),
        ]

        for p in patchers:
            p.start()

        # Proceed
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': date_po,
                }),
                (0, 0, {
                    'name': product_standard.name,
                    'product_id': product_standard.id,
                    'product_qty': 1.0,
                    'product_uom': product_standard.uom_po_id.id,
                    'price_unit': 40.0,
                    'date_planned': date_po,
                }),
            ],
        })
        po.button_confirm()

        line_product_average = po.order_line.filtered(lambda l: l.product_id == self.product1)
        line_product_standard = po.order_line.filtered(lambda l: l.product_id == product_standard)

        inv = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
            'invoice_date': date_invoice,
            'date': date_invoice,
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': self.product1.name,
                    'price_subtotal': 100.0,
                    'price_unit': 100.0,
                    'product_id': self.product1.id,
                    'purchase_line_id': line_product_average.id,
                    'quantity': 1.0,
                    'account_id': self.stock_input_account.id,
                }),
                (0, 0, {
                    'name': product_standard.name,
                    'price_subtotal': 70.0,
                    'price_unit': 70.0,
                    'product_id': product_standard.id,
                    'purchase_line_id': line_product_standard.id,
                    'quantity': 1.0,
                    'account_id': self.stock_input_account.id,
                })
            ]
        })

        inv.action_post()

        for p in patchers:
            p.stop()

        move_lines = inv.line_ids
        self.assertEqual(len(move_lines), 5)

        # Ensure no exchange difference move has been created
        self.assertTrue(all([not l.reconciled for l in move_lines]))

        # PAYABLE CHECK
        payable_line = move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')
        self.assertEqual(payable_line.amount_currency, -170.0)
        self.assertAlmostEqual(payable_line.balance, -85.00)

        # PRODUCTS CHECKS

        # NO EXCHANGE DIFFERENCE (average)
        # We ordered for a value of 100 EUR
        # But by the time we are invoiced for it
        # the foreign currency appreciated from 1.5 to 2.0
        # We still have to pay 100 EUR, which now values at 50 USD
        product_lines = move_lines.filtered(lambda l: l.product_id == self.product1)

        # Stock-wise, we have been invoiced 100 EUR, and we ordered 100 EUR
        # there is no price difference
        # However, 100 EUR should be converted at the time of the invoice
        stock_lines = product_lines.filtered(lambda l: l.account_id == self.stock_input_account)
        self.assertAlmostEqual(sum(stock_lines.mapped('amount_currency')), 100.00)
        self.assertAlmostEqual(sum(stock_lines.mapped('balance')), 50.00)

        # PRICE DIFFERENCE (STANDARD)
        # We ordered a product that should have cost 60 USD (120 EUR)
        # However, we effectively got invoiced 70 EUR (35 USD)
        product_lines = move_lines.filtered(lambda l: l.product_id == product_standard)

        stock_lines = product_lines.filtered(lambda l: l.account_id == self.stock_input_account)
        self.assertAlmostEqual(sum(stock_lines.mapped('amount_currency')), 120.00)
        self.assertAlmostEqual(sum(stock_lines.mapped('balance')), 60.00)

        price_diff_line = product_lines.filtered(lambda l: l.account_id == self.price_diff_account)
        self.assertEqual(price_diff_line.amount_currency, -50.00)
        self.assertAlmostEqual(price_diff_line.balance, -25.00)

    def test_average_realtime_with_delivery_anglo_saxon_valuation_multicurrency_different_dates(self):
        """
        The PO and invoice are in the same foreign currency.
        The delivery occurs in between PO validation and invoicing
        The invoice is created at an even different date
        This should create a price difference entry.
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        date_po = '2019-01-01'
        date_delivery = '2019-01-08'
        date_invoice = '2019-01-16'

        product_avg = self.product1_copy
        product_avg.write({
            'purchase_method': 'purchase',
            'name': 'AVG',
            'standard_price': 60,
        })

        # SetUp currency and rates
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", (self.usd_currency.id, company.id))
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.0,
            'currency_id': self.usd_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.5,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_delivery,
            'rate': 0.7,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_invoice,
            'rate': 2,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        # To allow testing validation of PO and Delivery
        today = date_po

        def _today(*args, **kwargs):
            return datetime.strptime(today, "%Y-%m-%d").date()

        def _now(*args, **kwargs):
            return datetime.strptime(today + ' 01:00:00', "%Y-%m-%d %H:%M:%S")

        patchers = [
            patch('odoo.fields.Date.context_today', _today),
            patch('odoo.fields.Datetime.now', _now),
        ]

        for p in patchers:
            p.start()

        # Proceed
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': product_avg.name,
                    'product_id': product_avg.id,
                    'product_qty': 1.0,
                    'product_uom': product_avg.uom_po_id.id,
                    'price_unit': 30.0,
                    'date_planned': date_po,
                })
            ],
        })
        po.button_confirm()

        line_product_avg = po.order_line.filtered(lambda l: l.product_id == product_avg)

        today = date_delivery
        picking = po.picking_ids
        (picking.move_ids
            .filtered(lambda l: l.purchase_line_id == line_product_avg)
            .write({'quantity_done': 1.0}))

        picking.button_validate()
        # 5 Units received at rate 0.7 = 42.86
        self.assertAlmostEqual(product_avg.standard_price, 42.86)

        today = date_invoice
        inv = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
            'invoice_date': date_invoice,
            'date': date_invoice,
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': product_avg.name,
                    'price_unit': 30.0,
                    'product_id': product_avg.id,
                    'purchase_line_id': line_product_avg.id,
                    'quantity': 1.0,
                    'account_id': self.stock_input_account.id,
                })
            ]
        })

        inv.action_post()

        for p in patchers:
            p.stop()

        self.assertRecordValues(inv.line_ids, [
            # pylint: disable=C0326
            {'balance': 15.0,   'amount_currency': 30.0,    'account_id': self.stock_input_account.id},
            {'balance': -15.0,  'amount_currency': -30.0,   'account_id': self.company_data['default_account_payable'].id},
        ])
        self.assertRecordValues(inv.line_ids.full_reconcile_id.reconciled_line_ids, [
            # pylint: disable=C0326
            {'balance': -42.86, 'amount_currency': -30.0,   'account_id': self.stock_input_account.id},
            {'balance': 15.0,   'amount_currency': 30.0,    'account_id': self.stock_input_account.id},
            {'balance': 27.86,  'amount_currency': 0.0,     'account_id': self.stock_input_account.id},
        ])

    def test_average_realtime_with_two_delivery_anglo_saxon_valuation_multicurrency_different_dates(self):
        """
        The PO and invoice are in the same foreign currency.
        The deliveries occur at different times and rates
        The invoice is created at an even different date
        This should create a price difference entry.
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency
        exchange_diff_journal = company.currency_exchange_journal_id.exists()

        date_po = '2019-01-01'
        date_delivery = '2019-01-08'
        date_delivery1 = '2019-01-10'
        date_invoice = '2019-01-16'
        date_invoice1 = '2019-01-20'

        self.product1.categ_id.property_valuation = 'real_time'
        self.product1.categ_id.property_cost_method = 'average'
        product_avg = self.product1_copy
        product_avg.write({
            'purchase_method': 'purchase',
            'name': 'AVG',
            'standard_price': 0,
        })

        # SetUp currency and rates
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", (self.usd_currency.id, company.id))
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.0,
            'currency_id': self.usd_currency.id,
            'company_id': company.id,
        })
        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.5,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_delivery,
            'rate': 0.7,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })
        self.env['res.currency.rate'].create({
            'name': date_delivery1,
            'rate': 0.8,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_invoice,
            'rate': 2,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })
        self.env['res.currency.rate'].create({
            'name': date_invoice1,
            'rate': 2.2,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        # To allow testing validation of PO and Delivery
        today = date_po

        def _today(*args, **kwargs):
            return datetime.strptime(today, "%Y-%m-%d").date()

        def _now(*args, **kwargs):
            return datetime.strptime(today + ' 01:00:00', "%Y-%m-%d %H:%M:%S")

        patchers = [
            patch('odoo.fields.Date.context_today', _today),
            patch('odoo.fields.Datetime.now', _now),
        ]

        for p in patchers:
            p.start()

        # Proceed
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'date_order': date_po,
            'order_line': [
                (0, 0, {
                    'name': product_avg.name,
                    'product_id': product_avg.id,
                    'product_qty': 10.0,
                    'product_uom': product_avg.uom_po_id.id,
                    'price_unit': 30.0,
                    'date_planned': date_po,
                })
            ],
        })
        po.button_confirm()

        line_product_avg = po.order_line.filtered(lambda l: l.product_id == product_avg)

        today = date_delivery
        picking = po.picking_ids
        (picking.move_ids
            .filtered(lambda l: l.purchase_line_id == line_product_avg)
            .write({'quantity_done': 5.0}))

        picking.button_validate()
        picking._action_done()  # Create Backorder
        # 5 Units received at rate 0.7 = 42.86
        self.assertAlmostEqual(product_avg.standard_price, 42.86)
        today = date_invoice
        inv = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
            'invoice_date': date_invoice,
            'date': date_invoice,
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': product_avg.name,
                    'price_unit': 20.0,
                    'product_id': product_avg.id,
                    'purchase_line_id': line_product_avg.id,
                    'quantity': 5.0,
                    'account_id': self.stock_input_account.id,
                })
            ]
        })

        inv.action_post()

        today = date_delivery1
        backorder_picking = self.env['stock.picking'].search([('backorder_id', '=', picking.id)])
        (backorder_picking.move_ids
            .filtered(lambda l: l.purchase_line_id == line_product_avg)
            .write({'quantity_done': 5.0}))
        backorder_picking.button_validate()
        # 5 Units received at rate 0.7 (42.86) + 5 Units received at rate 0.8 (37.50) = 40.18
        self.assertAlmostEqual(product_avg.standard_price, 40.18)

        today = date_invoice1
        inv1 = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
            'invoice_date': date_invoice1,
            'date': date_invoice1,
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': product_avg.name,
                    'price_unit': 40.0,
                    'product_id': product_avg.id,
                    'purchase_line_id': line_product_avg.id,
                    'quantity': 5.0,
                    'account_id': self.stock_input_account.id,
                })
            ]
        })

        inv1.action_post()

        for p in patchers:
            p.stop()

        ##########################
        #       Invoice 0        #
        ##########################

        self.assertRecordValues(inv.line_ids, [
            # pylint: disable=C0326
            {'balance': 50.0,   'amount_currency': 100.0,   'account_id': self.stock_input_account.id},
            {'balance': -50.0,  'amount_currency': -100.0,  'account_id': self.company_data['default_account_payable'].id},
            {'balance': -25.0,  'amount_currency': -50.0,   'account_id': self.price_diff_account.id},
            {'balance': 25.0,   'amount_currency': 50.0,    'account_id': self.stock_input_account.id},
        ])

        self.assertRecordValues(inv.line_ids.full_reconcile_id.reconciled_line_ids, [
            # pylint: disable=C0326
            # Exchange difference lines:
            {'balance': 46.43,      'amount_currency': 0.0},
            {'balance': 92.86,      'amount_currency': 0.0},
            # Other lines:
            {'balance': 50.0,       'amount_currency': 100.0},
            {'balance': 25.0,       'amount_currency': 50.0},
            {'balance': -214.29,    'amount_currency': -150.0},
        ])

        ##########################
        #       Invoice 1        #
        ##########################

        self.assertRecordValues(inv1.line_ids, [
            # pylint: disable=C0326
            {'balance': 90.91,  'amount_currency': 200.0,   'account_id': self.stock_input_account.id},
            {'balance': -90.91, 'amount_currency': -200.0,  'account_id': self.company_data['default_account_payable'].id},
            {'balance': 22.73,  'amount_currency': 50.0,    'account_id': self.price_diff_account.id},
            {'balance': -22.73, 'amount_currency': -50.0,   'account_id': self.stock_input_account.id},
        ])

        self.assertRecordValues(inv1.line_ids.full_reconcile_id.reconciled_line_ids, [
            # pylint: disable=C0326
            # Other lines:
            {'balance': -187.5,     'amount_currency': -150.0},
            {'balance': 90.91,      'amount_currency': 200.0},
            {'balance': -22.73,     'amount_currency': -50.0},
            # Exchange difference lines:
            {'balance': 119.32,     'amount_currency': 0.0},
        ])

    def test_anglosaxon_valuation_price_total_diff_discount(self):
        """
        PO:  price unit: 110
        Inv: price unit: 100
             discount:    10
        """
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        # Create PO
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 110.0
        order = po_form.save()
        order.button_confirm()

        # Receive the goods
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity_done = 1
        receipt.button_validate()

        # Create an invoice with a different price and a discount
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.invoice_date = invoice_form.date
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 100.0
            line_form.discount = 10.0
        invoice = invoice_form.save()
        invoice.action_post()

        # Check what was posted in the stock valuation account
        stock_valuation_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_valuation_account.id)])
        self.assertEqual(
            len(stock_valuation_aml), 2,
            "Two lines for the stock valuation account: one from the receipt (debit 110) and one from the bill (credit 20)")
        self.assertAlmostEqual(sum(stock_valuation_aml.mapped('debit')), 110)
        self.assertAlmostEqual(sum(stock_valuation_aml.mapped('credit')), 20, "Credit of 20 because of the difference between the PO and its invoice")

        # Check what was posted in stock input account
        input_aml = self.env['account.move.line'].search([('account_id','=', self.stock_input_account.id)])
        self.assertEqual(len(input_aml), 3, "Only two lines should have been generated in stock input account: one when receiving the product, two when making the invoice.")
        self.assertAlmostEqual(sum(input_aml.mapped('debit')), 110, "Total debit value on stock input account should be equal to the original PO price of the product.")
        self.assertAlmostEqual(sum(input_aml.mapped('credit')), 110, "Total credit value on stock input account should be equal to the original PO price of the product.")

    def test_anglosaxon_valuation_discount(self):
        """
        PO:  price unit: 100
        Inv: price unit: 100
             discount:    10
        """
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        # Create PO
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 100.0
        order = po_form.save()
        order.button_confirm()

        # Receive the goods
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity_done = 1
        receipt.button_validate()

        # Create an invoice with a different price and a discount
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.invoice_date = invoice_form.date
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.tax_ids.clear()
            line_form.discount = 10.0
        invoice = invoice_form.save()
        invoice.action_post()

        # Check what was posted in the stock valuation account
        stock_valuation_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_valuation_account.id)])
        self.assertEqual(len(stock_valuation_aml), 2, "Only one line should have been generated in the price difference account.")
        self.assertAlmostEqual(sum(stock_valuation_aml.mapped('debit')), 100)
        self.assertAlmostEqual(sum(stock_valuation_aml.mapped('credit')), 10, "Credit of 10 because of the 10% discount")

        # Check what was posted in stock input account
        input_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)])
        self.assertEqual(len(input_aml), 3, "Three lines generated in stock input account: one when receiving the product, two when making the invoice.")
        self.assertAlmostEqual(sum(input_aml.mapped('debit')), 100, "Total debit value on stock input account should be equal to the original PO price of the product.")
        self.assertAlmostEqual(sum(input_aml.mapped('credit')), 100, "Total credit value on stock input account should be equal to the original PO price of the product.")

    def test_anglosaxon_valuation_price_unit_diff_discount(self):
        """
        PO:  price unit:  90
        Inv: price unit: 100
             discount:    10
        """
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        # Create PO
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 90.0
        order = po_form.save()
        order.button_confirm()

        # Receive the goods
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity_done = 1
        receipt.button_validate()

        # Create an invoice with a different price and a discount
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.invoice_date = invoice_form.date
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 100.0
            line_form.discount = 10.0
        invoice = invoice_form.save()
        invoice.action_post()

        # Check if something was posted in the price difference account
        price_diff_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_valuation_account.id)])
        self.assertEqual(price_diff_aml.debit, 90, "Should have only one line in the stock valuation account, created by the receipt.")

        # Check what was posted in stock input account
        input_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)])
        self.assertEqual(len(input_aml), 2, "Only two lines should have been generated in stock input account: one when receiving the product, one when making the invoice.")
        self.assertAlmostEqual(sum(input_aml.mapped('debit')), 90, "Total debit value on stock input account should be equal to the original PO price of the product.")
        self.assertAlmostEqual(sum(input_aml.mapped('credit')), 90, "Total credit value on stock input account should be equal to the original PO price of the product.")

    def test_anglosaxon_valuation_price_unit_diff_avco(self):
        """
        Inv: price unit: 100
        """
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'average'
        self.product1.categ_id.property_valuation = 'real_time'
        self.product1.standard_price = 1.01

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2022-03-31',
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product1.id, 'quantity': 10.50, 'price_unit': 1.01, 'tax_ids': self.tax_purchase_a.ids})
            ]
        })

        # Check if something was posted in the stock valuation account.
        stock_val_aml = invoice.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        self.assertEqual(len(stock_val_aml), 0, "No line should have been generated in the stock valuation account.")
