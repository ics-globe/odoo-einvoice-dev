# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    l10n_fr_rounding_difference_loss_account_id = fields.Many2one(
        'account.account.template',
        string="Loss Account for Rounding Differences",
        help="Account used for losses from rounding the lines of French tax returns",
    )
    l10n_fr_rounding_difference_profit_account_id = fields.Many2one(
        'account.account.template',
        string="Profit Account for Rounding Differences",
        help="Account used for profits from rounding the lines of French tax returns",
    )

    def _load_company_accounts(self, account_ref, company):
        super()._load_company_accounts(account_ref, company)

        # Add the fields that will contain the accounts used for the
        # profit/loss from rounding lines of the french tax report
        company.write({
            field: account_ref[self[field]]
            for field in (
                'l10n_fr_rounding_difference_loss_account_id',
                'l10n_fr_rounding_difference_profit_account_id',
            )
            if account_ref.get(self[field])
        })

    @api.model
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        journal_data = super(AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict)
        if company.account_fiscal_country_id.code != 'FR':
            return journal_data

        for journal in journal_data:
            if journal['type'] in ('sale', 'purchase'):
                journal.update({'refund_sequence': True})
        return journal_data
