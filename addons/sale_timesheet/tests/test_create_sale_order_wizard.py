# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestCommonSaleTimesheet


@tagged('-at_install', 'post_install')
class TestCreateSaleOrderWizard(TestCommonSaleTimesheet, unittest.TestCase):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.project_global.partner_id = cls.partner_b

    def test_create_sale_order_with_project(self):
        self.assertFalse(self.project_global.sale_line_id)
        create_sale_order_wizard = self.env['create.sale.order.wizard'] \
            .with_context(active_model='project.project', active_id=self.project_global.id) \
            .create({})
        self.assertFalse(create_sale_order_wizard.line_ids, 'No lines should be generated when we instantiate the wizard.')
        self.assertEqual(
            create_sale_order_wizard.project_id,
            self.project_global,
            'Only one project is found in the wizard via its reference since the active_model and the active_id is a project.'
        )
        self.assertEqual(len(create_sale_order_wizard.reference_ids), 1, 'There should be one reference.')
        self.assertEqual(create_sale_order_wizard.reference_ids.res_model, 'project.project')
        self.assertEqual(create_sale_order_wizard.reference_ids.res_id, self.project_global.id)
        self.assertEqual(create_sale_order_wizard.reference_ids.resource_ref, self.project_global)

        wizard_line1, wizard_line2 = self.env['create.sale.order.line.wizard'] \
            .with_context(default_wizard_id=create_sale_order_wizard.id) \
            .create([
                {'product_id': self.product_delivery_timesheet1.id},
                {'employee_id': self.employee_user.id, 'product_id': self.product_delivery_timesheet2.id},
            ])
        self.assertEqual(
            wizard_line1.price_unit,
            self.product_delivery_timesheet1.lst_price,
            'By default, the price unit should the sell price defined in the product set in this line.')
        self.assertEqual(
            wizard_line2.price_unit,
            self.product_delivery_manual2.lst_price,
            'By default, the price unit should the sell price defined in the product set in this line.')
        sale_order = create_sale_order_wizard._create_sale_orders()
        self.assertEqual(len(sale_order), 1, 'Only one SO should be created in this wizard.')
        self.assertEqual(self.project_global.sale_order_id, sale_order, 'The Sale Order created with the wizard should be set on the project.')

        with self.assertRaises(UserError, msg='Check the user error is raise when the user wants to generate a SO for a project in which has already had one.'):
            create_sale_order_wizard._create_sale_orders()

    def test_create_sale_order_with_tasks_in_same_project(self):
        Task = self.env['project.task'].with_context(tracking_disable=True, default_project_id=self.project_global.id)
        task1 = Task.create({
            'name': 'Task 1',
            'sale_line_id': False,
        })
        task2 = Task.create({
            'name': 'Task 2',
            'sale_line_id': False,
            'timesheet_ids': [
                Command.create({
                    'name': '/',
                    'employee_id': self.employee_user.id,
                    'unit_amount': 1.0,
                }),
            ]
        })
        tasks = task1 + task2
        self.assertFalse(tasks.sale_line_id)
        create_sale_order_wizard = self.env['create.sale.order.wizard'] \
            .with_context(active_model='project.task', active_ids=tasks.ids) \
            .create({})
        self.assertFalse(create_sale_order_wizard.line_ids, 'No lines should be generated when we instantiate the wizard.')
        self.assertEqual(
            create_sale_order_wizard.project_id,
            self.project_global,
            'Only one project is found in the wizard via its reference since the both tasks given in active_ids are linked to the same project.'
        )
        self.assertEqual(len(create_sale_order_wizard.reference_ids), 2, 'There should be 2 references since 2 tasks are passed in the active_ids.')
        self.asserTrue(all(ref.res_model == 'project.task' for ref in create_sale_order_wizard.reference_ids.res_model))
        self.assertEqual(create_sale_order_wizard.reference_ids.mapped('res_id'), tasks.ids)
        self.assertEqual(create_sale_order_wizard.reference_ids.resource_ref, tasks)

    def test_create_sale_order_with_tasks_in_different_projects(self):
        ...

    def test_create_sale_order_with_timesheets_in_same_project(self):
        timesheets = self.env['account.analytic.line'].create([

        ])
        self.assertFalse(timesheets.so_line)
        create_sale_order_wizard = self.env['create.sale.order.wizard'] \
            .with_context(active_model='account.analytic.line', active_ids=timesheets.ids) \
            .create({})
        self.assertFalse(create_sale_order_wizard.line_ids, 'No lines should be generated when we instantiate the wizard.')
        self.assertEqual(
            create_sale_order_wizard.project_id,
            self.project_global,
            'Only one project is found in the wizard via its reference since the active_model and the active_id is a project.'
        )
        self.assertEqual(len(create_sale_order_wizard.reference_ids), 1, 'There should be one reference.')
        self.assertEqual(create_sale_order_wizard.reference_ids.res_model, 'project.project')
        self.assertEqual(create_sale_order_wizard.reference_ids.res_id, self.project_global.id)
        self.assertEqual(create_sale_order_wizard.reference_ids.resource_ref, self.project_global)

    def test_create_sale_order_with_timesheets_in_different_projects(self):
        ...
