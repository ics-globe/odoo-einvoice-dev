# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class Task(models.Model):
    _inherit = 'project.task'

    timeoff_type_ids = fields.One2many('hr.leave.type', 'timesheet_task_id', string="Task Time off Types")
    is_timeoff_task = fields.Boolean(string="Is Time off Task", compute="_compute_is_timeoff_task",
        search="_search_is_timeoff_task")

    @api.depends('timeoff_type_ids', 'company_id.leave_timesheet_task_id')
    def _compute_is_timeoff_task(self):
        timeoff_tasks = self.filtered(lambda task: task.timeoff_type_ids or task.company_id.leave_timesheet_task_id == task)
        timeoff_tasks.update({'is_timeoff_task': True})

        (self - timeoff_tasks).update({'is_timeoff_task': False})

    def _search_is_timeoff_task(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported'))

        timeoff_tasks_ids = self.env['project.task'].search(['|',
            ('timeoff_type_ids.timesheet_task_id', '!=', False),
            ('id', '=', self.env.company.leave_timesheet_task_id.id)])

        if operator == '!=':
            value = not value

        return [('id', 'in' if value else 'not in', timeoff_tasks_ids.ids)]
