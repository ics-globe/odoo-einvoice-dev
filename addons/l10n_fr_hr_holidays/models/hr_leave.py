# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo import fields, models, api

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    l10n_fr_date_to = fields.Datetime('End Date For French Rules', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            employee = self.env['hr.employee'].browse(vals['employee_id']).sudo()
            employee_calendar = employee.resource_calendar_id
            company_calendar = employee.company_id.resource_calendar_id
            vals['date_to'] = self._get_fr_new_date_to(vals, employee_calendar, company_calendar)
        return super().create(vals_list)

    def _calendar_works_on_date(self, CalendarAttendance, calendar, working_days, date):
        dayofweek = str(date.weekday())
        if calendar.two_weeks_calendar:
            weektype = str(CalendarAttendance.get_week_type(date))
            return working_days[weektype][dayofweek]
        return working_days[False][dayofweek]

    def _get_working_hours(self, calendar):
        working_days = defaultdict(lambda: defaultdict(lambda: False))
        for attendance in calendar.attendance_ids:
            working_days[attendance.week_type][attendance.dayofweek] = True
        return working_days

    def _get_fr_new_date_to(self, vals, employee_calendar, company_calendar):
        employee_working_days = self._get_working_hours(employee_calendar)
        company_working_days = self._get_working_hours(company_calendar)

        CalendarAttendance = self.env['resource.calendar.attendance']
        date_target = datetime.fromisoformat(vals['date_to'])
        new_date_to = date_target
        date_target += relativedelta(days=1)
        while not self._calendar_works_on_date(CalendarAttendance, employee_calendar, employee_working_days, date_target):
            if self._calendar_works_on_date(CalendarAttendance, company_calendar, company_working_days, date_target):
                new_date_to = date_target
            date_target += relativedelta(days=1)

        return new_date_to

    def _get_fr_number_of_days(self, employee, date_from, date_to, employee_calendar, company_calendar):
        self.ensure_one()

        self.l10n_fr_date_to = False
        # We can fill the holes using the company calendar as default
        # What we need to compute is how much we will need to push date_to in order to account for the lost days
        # This gets even more complicated in two_weeks_calendars
        employee_working_days = self._get_working_hours(employee_calendar)
        company_working_days = self._get_working_hours(company_calendar)

        CalendarAttendance = self.env['resource.calendar.attendance']
        if self.request_unit_half:
            # In normal workflows request_unit_half implies that date_from and date_to are the same
            # request_unit_half allows us to choose between `am` and `pm`
            # In a case where we work from mon-wed and request a half day in the morning
            # we do not want to push date_to since the next work attendance is actually in the afternoon
            date_from_weektype = str(CalendarAttendance.get_week_type(date_from))
            date_from_dayofweek = str(date_from.weekday())
            # Fetch the attendances we care about
            attendance_ids = employee_calendar.attendance_ids.filtered(lambda a:
                a.dayofweek == date_from_dayofweek and\
                (not employee_calendar.two_weeks_calendar or a.week_type == date_from_weektype))
            if len(attendance_ids) == 2 and self.request_date_from_period == 'am':
                # The employee took the morning off on a day where he works the afternoon aswell
                attendance = attendance_ids[0] if attendance_ids[0].day_period == 'morning' else attendance_ids[1]
                return {'days': 0.5, 'hours': attendance.hour_to - attendance.hour_from}
        # Check calendars for working days until we find the right target, start at date_to + 1 day
        # Postpone date_target until the next working day
        date_start = date_from
        date_target = date_to + relativedelta(days=1)
        counter = 0
        while not self._calendar_works_on_date(CalendarAttendance, employee_calendar, employee_working_days, date_start):
            date_start += relativedelta(days=1)
        while not self._calendar_works_on_date(CalendarAttendance, employee_calendar, employee_working_days, date_target):
            date_target += relativedelta(days=1)
            counter += 1
            # Check that we aren't running an infinite loop (it would mean that employee_calendar is empty and
            # company_calendar works every day)
            # Allow up to 14 days for two weeks calendars.
            if counter > 14:
                # Default behaviour
                result = employee._get_work_days_data_batch(date_start, date_to, calendar=employee_calendar)[employee.id]
                if self.request_unit_half and result['hours'] > 0:
                    result['days'] = 0.5
                return result
        date_target = datetime.combine(date_target.date(), datetime.min.time())
        self.l10n_fr_date_to = date_target
        return employee._get_work_days_data_batch(date_start, date_target, calendar=company_calendar)[employee.id]

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """
        In french time off laws, if an employee has a part time contract, when taking time off
        before one of his off day (compared to the company's calendar) it should also count the time
        between the time off and the next calendar work day/company off day (weekends).

        For example take an employee working mon-wed in a company where the regular calendar is mon-fri.
        If the employee were to take a time off ending on wednesday, the legal duration would count until friday.

        Returns a dict containing two keys: 'days' and 'hours' with the value being the duration for the requested time period.
        """
        basic_amount = super()._get_number_of_days(date_from, date_to, employee_id)
        if employee_id and (basic_amount['days'] or basic_amount['hours']):
            employee = self.env['hr.employee'].browse(employee_id).sudo()
            company = employee.company_id
            if company.country_id.code == 'FR' and company.resource_calendar_id:
                calendar = self._get_calendar()
                if calendar and calendar != company.resource_calendar_id:
                    return self._get_fr_number_of_days(employee, date_from, date_to, calendar, company.resource_calendar_id)
        return basic_amount
