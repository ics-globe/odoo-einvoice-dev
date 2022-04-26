# -*- coding: utf-8 -*-

from odoo import fields
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtStock(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'My Company PT',
            'street': '250 Executive Park Blvd, Suite 3400',
            'city': 'Lisboa',
            'zip': '9415-343',
            'company_registry': '123456',
            'phone': '+351 11 11 11 11',
            'country_id': cls.env.ref('base.pt').id,
            'currency_id': cls.env.ref('base.EUR').id,
            'vat': 'PT123456789',
        })
        cls.location = cls.env['stock.location'].create({
            'name': 'Location PT 1',
            'usage': 'internal',
            'company_id': cls.company.id,
        })
        cls.location2 = cls.env['stock.location'].create({
            'name': 'Location PT 2',
            'usage': 'internal',
            'company_id': cls.company.id,
        })
        cls.picking_type_out = cls.env['stock.picking.type'].create({
            'name': 'Picking Out',
            'sequence_code': 'OUT',
            'code': 'outgoing',
            'reservation_method': 'at_confirm',
            'company_id': cls.company.id,
            'warehouse_id': False,
        })
        cls.picking_type_in = cls.env['stock.picking.type'].create({
            'name': 'Picking In',
            'sequence_code': 'IN',
            'code': 'incoming',
            'reservation_method': 'at_confirm',
            'company_id': cls.company.id,
            'warehouse_id': False,
        })

    def _create_picking(self, picking_type):
        picking = self.env['stock.picking'].create({
            'move_type': 'direct',
            'location_id': self.location.id,
            'location_dest_id': self.location2.id,
            'picking_type_id': picking_type,
        })
        picking.company_id = self.company.id
        move = self._create_move(picking)
        picking.move_line_ids |= move.move_line_ids
        return picking

    def _create_move(self, picking):
        move_line = self.env['stock.move.line'].create({
            'company_id': self.company.id,
            'product_id': self.productA.id,
            'product_uom_id': self.productA.uom_id.id,
            'reserved_uom_qty': 10,
            'date': fields.Datetime.now(),
            'location_id': self.location.id,
            'location_dest_id': self.location2.id,
            'qty_done': 10,
        })
        move = self.env['stock.move'].create({
            'company_id': self.company.id,
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location.id,
            'location_dest_id': self.location2.id,
            'state': 'done',
            'move_line_ids': move_line,
        })
        return move

    def test_l10n_pt_stock_hash_sequence(self):
        for picking_type, expected in (
                (self.picking_type_out.id, '0'),
                (self.picking_type_out.id, '1'),
                (self.picking_type_out.id, '2'),
                (self.picking_type_in.id, False),
                (self.picking_type_out.id, '3'),
                (self.picking_type_in.id, False),
                (self.picking_type_out.id, '4'),
        ):
            picking = self._create_picking(picking_type)
            picking._action_done()
            self.assertEqual(picking.inalterable_hash, expected)

    def test_l10n_pt_stock_hash_inalterability(self):
        picking = self._create_picking(self.picking_type_out.id)
        picking._action_done()
        with self.assertRaises(UserError):
            picking['inalterable_hash'] = 'fake_hash'
        with self.assertRaises(UserError):
            picking['date_done'] = fields.Date.from_string('2000-01-01')
        with self.assertRaises(UserError):
            picking['create_date'] = fields.Datetime.now()

    def test_l10n_pt_stock_document_no(self):
        for expected in ['outgoing OUT/1', 'outgoing OUT/2', 'outgoing OUT/3']:
            picking = self._create_picking(self.picking_type_out.id)
            picking._action_done()
            self.assertEqual(picking.l10n_pt_document_no, expected)
