# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    holiday_id = fields.Many2one("hr.leave", string='Leave Request')
    global_leave_id = fields.Many2one("resource.calendar.leaves", string="Global Time Off", ondelete='cascade')
    task_id = fields.Many2one(domain="[('company_id', '=', company_id), ('project_id.allow_timesheets', '=', True),\
        ('project_id', '=?', project_id), ('is_timeoff_task', '=', False)]")

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_leave(self):
        if any(line.holiday_id for line in self):
            raise UserError(_('You cannot delete timesheets linked to time off. Please, cancel the time off instead.'))

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            Task = self.env['project.task']
            for vals in vals_list:
                if vals.get('task_id') and Task.browse(vals['task_id']).is_timeoff_task:
                    raise UserError(_('"You cannot create timesheets that are linked to time off. For that, please use the Time Off application.'))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su and self.filtered('holiday_id'):
            raise UserError(_('"You cannot update timesheets that are linked to time off. For that, please use the Time Off application.'))
        return super().write(vals)
