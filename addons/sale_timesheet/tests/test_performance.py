# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import users, warmup

from .common import TestCommonSaleTimesheet


class TestSaleTimesheetPerformance(TestCommonSaleTimesheet):
    @users('__system__')
    @warmup
    def test_performance_determined_so_line(self):
        """ Test when the invoicing configuration of the project changes, the number of query to determine
            the SOL for all timesheets in this project

            Test Case:
            =========
            1) Create another employee to have at least 3 employees for the test.
            2) Create 10 tasks in project_task_rate
            3) Create 10 timesheets for each task for some employees
            4) Change the configuration of the project to have employee rate instead of task rate
            +            5) Check the number of queries.
        """
        georges_emp = self.env['hr.employee'].with_context(tracking_disable=True).create({
            'name': 'Georges',
            'timesheet_cost': 30,
        })
        tasks = self.env['project.task'].with_context(tracking_disable=True).create([
            {
                'name': 'Test Task %s' % i,
                'project_id': self.project_task_rate.id,
            } for i in range(1, 11)
        ])

        for task in tasks:
            self.env['account.analytic.line'].with_context(tracking_disable=True).create([{
                'name': 'Test Line %s' % i,
                'unit_amount': 1,
                'employee_id': self.employee_manager.id if i < 4 else self.employee_user.id if i < 7 else georges_emp.id,
                'project_id': self.project_task_rate.id,
                'task_id': task.id,
            } for i in range(1, 11)])

        with self.assertQueryCount(__system__=148):
            self.project_task_rate.with_context(tracking_disable=True).write({
                'partner_id': self.so.partner_id.id,
                'sale_line_id': self.so.order_line[0].id,
                'sale_line_employee_ids': [
                    Command.create({
                        'employee_id': self.employee_user.id,
                        'sale_line_id': self.so.order_line[1].id,
                    }),
                    Command.create({
                        'employee_id': georges_emp.id,
                        'sale_line_id': self.so.order_line[-1].id
                    })
                ]
            })
