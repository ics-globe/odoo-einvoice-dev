# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import timezone, UTC
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta
from odoo.tools import date_utils
from odoo.osv import expression

class CalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    holiday_id = fields.Many2one("hr.leave", string='Leave Request')

    @api.constrains('date_from', 'date_to', 'calendar_id')
    def _check_compare_dates(self):
        all_existing_leaves = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('company_id', 'in', self.company_id.ids),
            ('date_from', '<=', max(self.mapped('date_to'))),
            ('date_to', '>=', min(self.mapped('date_from'))),
        ])
        for record in self:
            if not record.resource_id:
                existing_leaves = all_existing_leaves.filtered(lambda leave:
                        record.id != leave.id
                        and record['company_id'] == leave['company_id']
                        and record['date_from'] <= leave['date_to']
                        and record['date_to'] >= leave['date_from'])
                if record.calendar_id:
                    existing_leaves = existing_leaves.filtered(lambda l: not l.calendar_id or l.calendar_id == record.calendar_id)
                if existing_leaves:
                    raise ValidationError(_('Two public holidays cannot overlap each other for the same working hours.'))

    def _get_domain(self, time_domain_dict):
        domain = []
        for date in time_domain_dict:
            domain = expression.OR([domain, [
                    ('date_to', '>', date['date_from']),
                    ('date_from', '<', date['date_to'])]
            ])
        return expression.AND([domain, [('state', '!=', 'refuse'), ('active', '=', True)]])

    def _get_time_domain_dict(self):
        return [{
            'date_from' : record.date_from,
            'date_to' : record.date_to
        } for record in self if not record.resource_id]

    def _split_leave_on_gto(self, leave, gto): #gto = global time off
        leave_start = date_utils.start_of(leave.date_from, 'day')
        leave_end = date_utils.end_of(leave.date_to - timedelta(seconds=1), 'day')
        gto_start = date_utils.start_of(gto['date_from'], 'day')
        gto_end = date_utils.end_of(gto['date_to'], 'day')
        leave_tz = timezone(leave.employee_id.resource_id.tz)

        if gto_start <= leave_start\
                and gto_end > leave_start\
                and gto_end < leave_end:
            leave.write({
                'date_from': leave_tz.localize(gto_end + timedelta(seconds=1))\
                        .astimezone(UTC).replace(tzinfo=None)
            })
            return self.env['hr.leave'].sudo()
        if gto_start > leave_start\
                and gto_end < leave_end:
            copys = {
                'date_from': leave.date_from,
                'date_to': leave_tz.localize(gto_start - timedelta(seconds=1))\
                        .astimezone(UTC).replace(tzinfo=None)
            }
            leave.write({
                'date_from': leave_tz.localize(gto_end + timedelta(seconds=1))\
                        .astimezone(UTC).replace(tzinfo=None)
            })
            return leave.copy(copys)
        if gto_start > leave_start\
                and gto_start < leave_end\
                and gto_end >= leave_end:
            leave.write({
                'date_to': leave_tz.localize(gto_start - timedelta(seconds=1))\
                        .astimezone(UTC).replace(tzinfo=None)
            })
            return self.env['hr.leave'].sudo()

    def _split_leave(self, leave, time_domain_dict):
        new_leaves = self.env['hr.leave'].sudo()
        for record in sorted(
                filter(lambda r: r['date_to'] > leave.date_from and r['date_from'] < leave.date_to, time_domain_dict),
                key=lambda r: r['date_from']):
            new_leave = self._split_leave_on_gto(leave, record)
            if new_leave:
                new_leaves |= new_leave
        return new_leaves

    def _reevaluate_leaves(self, time_domain_dict):
        if not time_domain_dict:
            return

        domain = self._get_domain(time_domain_dict)
        leaves = self.env['hr.leave'].search(domain)
        if not leaves:
            return

        previous_durations = leaves.mapped('number_of_days')
        previous_states = leaves.mapped('state')
        leaves.sudo().write({
            'state': 'draft',
        })
        self.env.add_to_compute(self.env['hr.leave']._fields['number_of_days'], leaves)
        sick_time_status = self.env.ref('hr_holidays.holiday_status_sl')
        for previous_duration, leave, state in zip(previous_durations, leaves, previous_states):
            duration_difference = previous_duration - leave.number_of_days
            if duration_difference > 0 and leave['holiday_allocation_id'] and leave.number_of_days == 0.0:
                message = _("Due to a change in global time offs, you have been granted %s day(s) back.", duration_difference)
                leave._notify_change(message)
            if leave.number_of_days > previous_duration\
                    and leave.holiday_status_id not in sick_time_status:
                new_leaves = self._split_leave(leave, time_domain_dict)
                leaves |= new_leaves
                previous_states += [state for i in range(len(new_leaves))]

        for state, leave in zip(previous_states, leaves):
            leave.write({'state': state})

        for leave in leaves:
            if leave.number_of_days == 0.0:
                leave._force_cancel(_("a new public holiday completely overrides this leave."), 'mail.mt_comment')

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        time_domain_dict = res._get_time_domain_dict()
        self._reevaluate_leaves(time_domain_dict)
        return res

    def write(self, vals):
        time_domain_dict = self._get_time_domain_dict()
        res = super().write(vals)
        time_domain_dict.extend(self._get_time_domain_dict())
        self._reevaluate_leaves(time_domain_dict)

        return res

    def unlink(self):
        time_domain_dict = self._get_time_domain_dict()
        res = super().unlink()
        self._reevaluate_leaves(time_domain_dict)

        return res

class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    associated_leaves_count = fields.Integer("Leave Count", compute='_compute_associated_leaves_count')

    def _compute_associated_leaves_count(self):
        leaves_read_group = self.env['resource.calendar.leaves'].read_group(
            [('resource_id', '=', False)],
            ['calendar_id'],
            ['calendar_id']
        )
        result = dict((data['calendar_id'][0] if data['calendar_id'] else 'global', data['calendar_id_count']) for data in leaves_read_group)
        global_leave_count = result.get('global', 0)
        for calendar in self:
            calendar.associated_leaves_count = result.get(calendar.id, 0) + global_leave_count
