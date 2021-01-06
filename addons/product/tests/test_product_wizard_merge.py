# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestProductWizardMerge(HttpCase):
    def test_01_merge_2_product_templates_without_variants_merge_product_product(self):
        """The goal of this test is to make sure wizard can merge 2 products and the variants."""

        pt_1 = self.env.ref('product.product_product_5') # Corner Desk Right Sit
        pt_1_id = pt_1.id
        pt_1_default_code = pt_1.default_code
        pt_1_list_price = pt_1.list_price
        pt_1_standard_price = pt_1.standard_price

        pt_2 = self.env.ref('product.product_product_13') # Corner Desk Left Sit

        self.start_tour("/", 'product_wizard_merge_test_01', login="admin")

        self.assertEqual(pt_1_id, pt_1.exists().id, "The first product (the smallest id) must be there")
        self.assertFalse(pt_2.exists(), "The second product must be removed because it's merged")
        self.assertEqual(pt_1_default_code, pt_1.default_code, "Should keep the first product default code")
        self.assertEqual(pt_1_list_price, pt_1.list_price, "Should keep the first product list price")
        self.assertEqual(pt_1_standard_price, pt_1.standard_price, "Should keep the first product standard price")
