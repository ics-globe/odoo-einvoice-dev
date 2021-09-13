# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import date_utils


class KarmaTracking(models.Model):
    _name = 'gamification.karma.tracking'
    _description = 'Track Karma Changes'
    _rec_name = 'user_id'
    _order = 'user_id, tracking_date desc, id desc'

    def _get_selection_origin(self):
        return [('res.users', 'User')]

    user_id = fields.Many2one('res.users', 'User', index=True, required=True, ondelete='cascade')
    old_value = fields.Integer('Old Karma Value', compute='_compute_old_value', store=True)
    new_value = fields.Integer('New Karma Value', required=True)
    consolidated = fields.Boolean('Consolidated')

    tracking_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    reason = fields.Text(default=lambda self: _('Added Manually'), string='Description')
    origin_ref = fields.Reference(
        string='Source',
        selection=lambda self: self._get_selection_origin(),
        default=lambda self: f'res.users,{self.env.user.id}',
    )

    @api.depends('user_id')
    def _compute_old_value(self):
        if not self.ids:
            self.old_value = 0
            return
        self.env['gamification.karma.tracking'].flush()
        query = """
            SELECT DISTINCT ON(current.id) current.id AS tracking_id, previous.new_value AS new_value
              FROM gamification_karma_tracking AS current
              JOIN gamification_karma_tracking AS previous
                ON current.user_id = previous.user_id
             WHERE (previous.tracking_date < current.tracking_date
                OR previous.id < current.id)
               AND current.id = ANY(%(tracking_ids)s)
          ORDER BY current.id, previous.tracking_date DESC, previous.id DESC
        """
        params = {'tracking_ids': self.filtered(lambda t: not t.consolidated).ids}
        self._cr.execute(query, params)
        results = self._cr.dictfetchall()
        values = {
            result['tracking_id']: result['new_value']
            for result in results
        }
        for tracking in self:
            if tracking.consolidated:
                continue
            tracking.old_value = values.get(tracking.id, 0)

    @api.model
    def _consolidate_cron(self):
        """Consolidate the trackings 2 months ago."""
        today = fields.Datetime.today()
        from_date = date_utils.start_of(today, 'month') - relativedelta(months=2)
        return self._process_consolidate(from_date)

    def _process_consolidate(self, from_date):
        """Consolidate the karma trackings, from the given date month.

        The consolidation keeps, for each user, the oldest "old_value" and the most recent
        "new_value", creates a new karma tracking with those values and removes all karma
        trackings between those dates.
        """
        self.env['gamification.karma.tracking'].flush()

        from_date = date_utils.start_of(from_date, 'month')
        end_date = date_utils.end_of(date_utils.end_of(from_date, 'month'), 'day')

        select_query = """
        WITH old_tracking AS (
            SELECT DISTINCT ON (user_id) user_id, old_value, tracking_date
              FROM gamification_karma_tracking
             WHERE tracking_date BETWEEN %(from_date)s
               AND %(end_date)s
               AND consolidated IS NOT TRUE
          ORDER BY user_id, tracking_date ASC, id ASC
        )
            SELECT DISTINCT ON (nt.user_id)
                            nt.user_id,
                            ot.old_value AS old_value,
                            nt.new_value AS new_value,
                            ot.tracking_date AS from_tracking_date,
                            nt.tracking_date AS to_tracking_date
              FROM gamification_karma_tracking AS nt
              JOIN old_tracking AS ot
                   ON ot.user_id = nt.user_id
             WHERE nt.tracking_date BETWEEN %(from_date)s
               AND %(end_date)s
               AND nt.consolidated IS NOT TRUE
          ORDER BY nt.user_id, nt.tracking_date DESC, id DESC
        """

        self.env.cr.execute(select_query, {
            'from_date': from_date,
            'end_date': end_date,
        })
        results = self.env.cr.dictfetchall()
        if results:
            self.create([{
                'consolidated': True,
                'new_value': result['new_value'],
                'old_value': result['old_value'],
                'origin_ref': f'res.users,{self.env.user.id}',
                'reason': _(
                    'Consolidation from %s to %s',
                    result['from_tracking_date'].strftime('%Y-%m-%d'),
                    result['to_tracking_date'].strftime('%Y-%m-%d'),
                ),
                'tracking_date': fields.Datetime.to_string(from_date),
                'user_id': result['user_id'],
            } for result in results])

            self.search([
                ('tracking_date', '>=', from_date),
                ('tracking_date', '<=', end_date),
                ('consolidated', '!=', True)]
            ).unlink()
        return True
