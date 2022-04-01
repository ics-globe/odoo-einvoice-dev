# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    def _check_if_error(self):
        res = super()._check_if_error()
        outside_calendar = self._mark_leaves_outside_schedule()
        return res or outside_calendar

    def _mark_leaves_outside_schedule(self):
        french_part_time_work_entries = self.filtered(lambda w:
            w.company_id.country_id.code == 'FR'
            and w.employee_id.resource_calendar_id != w.company_id.resource_calendar_id)
        if not french_part_time_work_entries:
            return super()._mark_leaves_outside_schedule()
        other_work_entries = self - french_part_time_work_entries
        return other_work_entries._mark_leaves_outside_schedule()