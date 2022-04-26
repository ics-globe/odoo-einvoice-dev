# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.model
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        journal_data = super()._prepare_all_journals(acc_template_ref, company, journals_dict)
        if company.account_fiscal_country_id.code != 'PT':
            return journal_data
        for journal in journal_data:
            if journal['type'] in ('sale', 'purchase'):
                journal.update({'restrict_mode_hash_table': True})
        return journal_data
