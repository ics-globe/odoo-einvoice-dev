# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_website_visitor_count = fields.Boolean('Visitors')
    kpi_website_visitor_count_value = fields.Integer(compute='_compute_kpi_website_visitors_count_value')
    kpi_website_track_count = fields.Boolean('Tracked page views')  # Non uniq
    kpi_website_track_count_value = fields.Integer(compute='_compute_kpi_website_track_count_value')

    def _compute_website_visitor_count(self, website_ids, start, end):
        if len(website_ids) == 0:
            return 0
        # The query takes into account that some website_visitor are the same visitor through parent_id
        self._cr.execute("""
            SELECT count(distinct COALESCE(v.parent_id, v.id))
                FROM website_visitor AS v
                JOIN website_track AS t ON t.visitor_id = v.id AND t.visit_datetime >= %(start)s AND t.visit_datetime < %(end)s
                WHERE v.website_id IN %(website_ids)s""", {'website_ids': website_ids, 'start': start, 'end': end})
        return self._cr.fetchone()[0]

    def _compute_website_track_count(self, website_ids, start, end):
        return self.env['website.track'].search_count(
            [('visitor_id.website_id', 'in', website_ids),
             ('visit_datetime', '>=', start),
             ('visit_datetime', '<', end)]) if len(website_ids) > 0 else 0

    def _compute_by_websites_gen(self, compute_kpi_by_ctx):
        """ Compute a value for each record using compute_kpi_by_ctx and yield the record and the computed value.
        compute_kpi_by_ctx receives a kpi parameter tuple (website_ids, start, end) and return the computed kpi.
        """
        # Following dicts are for memoization of partial results during the loop (lru_cache not usable)
        website_ids_by_company = dict()
        visitor_cnt_by_ctx = dict()
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            website_ids = website_ids_by_company[company.id] if company.id in website_ids_by_company else \
                website_ids_by_company.setdefault(company.id, tuple(
                    self.env['website'].search([('company_id', '=', company.id)]).ids))
            ctx = (website_ids, start, end)
            yield record, visitor_cnt_by_ctx[ctx] if ctx in visitor_cnt_by_ctx else \
                visitor_cnt_by_ctx.setdefault(ctx, compute_kpi_by_ctx(website_ids, start, end))

    def _compute_kpi_website_visitors_count_value(self):
        """ Compute the aggregated unique visitor of the websites company.
        Note that this computation relies on website_visitor which may create multiple visitor for the same user
        (indeed the user is not always identified).
        """
        for record, value in self._compute_by_websites_gen(self._compute_website_visitor_count):
            record.kpi_website_visitor_count_value = value

    def _compute_kpi_website_track_count_value(self):
        for record, value in self._compute_by_websites_gen(self._compute_website_track_count):
            record.kpi_website_track_count_value = value
