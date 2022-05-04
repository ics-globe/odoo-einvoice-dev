# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, Command, _


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _get_template_data(self):
        if self.env.company.chart_template != 'be':
            return super()._get_template_data()
        return {
            'bank_account_code_prefix': '550',
            'cash_account_code_prefix': '570',
            'transfer_account_code_prefix': '580',
            'currency_id': 'base.EUR',
            'country_id': 'base.be',
            'property_account_receivable_id': 'a400',
            'property_account_payable_id': 'a440',
            'property_account_expense_categ_id': 'a600',
            'property_account_income_categ_id': 'a7000',
            'expense_currency_exchange_account_id': 'a654',
            'income_currency_exchange_account_id': 'a754',
            'property_tax_payable_account_id': 'a4512',
            'property_tax_receivable_account_id': 'a4112',
            'default_pos_receivable_account_id': 'a4001',
            'account_journal_suspense_account_id': 'a499',
        }

    def _get_chart_template_data(self):
        res = super()._get_chart_template_data()
        if self.env.company.chart_template == 'be':
            res['account.fiscal.position'] = self._get_fiscal_position()
        return res

    def _get_res_company(self):
        cid = self.env.company.id
        if self.env.company.chart_template == 'be':
            return {
                self.env.company.get_metadata()[0]['xmlid']: {
                    'currency_id': "base.EUR",
                    'account_fiscal_country_id': "base.be",
                    # 'default_cash_difference_income_account_id': f'account.{cid}_cash_diff_income',
                    # 'default_cash_difference_expense_account_id': f'account.{cid}_cash_diff_expense',
                    # 'account_cash_basis_base_account_id': f'account.{cid}_cash_diff_income',  # TODO
                    # 'account_default_pos_receivable_account_id': f'account.{cid}_cash_diff_income',  # TODO
                    # 'income_currency_exchange_account_id': f'account.{cid}_income_currency_exchange',
                    # 'expense_currency_exchange_account_id': f'account.{cid}_expense_currency_exchange',
                }
            }
        return super()._get_res_company()

    def _get_account_journal(self):
        cid = self.env.company.id
        data = super()._get_account_journal()
        if self.env.company.chart_template == 'be':
            data[f"{cid}_sale"].update({
                'default_account_id': f'account.{cid}_a7000',
                'refund_sequence': True,
            })
            data[f"{cid}_purchase"].update({
                'default_account_id': f'account.{cid}_a600',
                'refund_sequence': True,
            })
            data[f"{cid}_cash"]['suspense_account_id'] = f'account.{cid}_a499'
            data[f"{cid}_bank"]['suspense_account_id'] = f'account.{cid}_a499'
        return data

    def _get_fiscal_position(self):
        cid = self.env.company.id
        return {
            f"{cid}_fiscal_position_template_1": {
                'sequence': 1,
                'name': _("Régime National"),
                'auto_apply': True,
                'vat_required': True,
                'country_id': 'base.be',
            },
            f"{cid}_fiscal_position_template_5": {
                'sequence': 2,
                'name': _("EU privé"),
                'auto_apply': True,
                'country_group_id': 'base.europe',
            },
            f"{cid}_fiscal_position_template_3": {
                'sequence': 3,
                'name': _("Régime Intra-Communautaire"),
                'auto_apply': True,
                'vat_required': True,
                'country_group_id': 'base.europe',
                'account_ids': [
                    Command.create({
                        'account_src_id': f'account.{cid}_a7000',
                        'account_dest_id': f'account.{cid}_a7001',
                    }),
                    Command.create({
                        'account_src_id': f'account.{cid}_a7010',
                        'account_dest_id': f'account.{cid}_a7011',
                    }),
                    Command.create({
                        'account_src_id': f'account.{cid}_a7050',
                        'account_dest_id': f'account.{cid}_a7051',
                    }),
                ],
                'tax_ids': [
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-00',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-00-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-06',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-06-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-12',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-12-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-21',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-21-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-00-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-00-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-00-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-00-EU-G',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-EU-G',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-EU-G',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-EU-S',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-EU-G',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-00',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-00-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-06',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-06-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-12',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-12-EU',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-21',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-21-EU',
                    }),
                ],
            },
            f"{cid}_fiscal_position_template_2": {
                'sequence': 4,
                'name': _("Régime Extra-Communautaire"),
                'auto_apply': True,
                'account_ids': [
                    Command.create({
                        'account_src_id': f'account.{cid}_a7000',
                        'account_dest_id': f'account.{cid}_a7002',
                    }),
                    Command.create({
                        'account_src_id': f'account.{cid}_a7010',
                        'account_dest_id': f'account.{cid}_a7012',
                    }),
                    Command.create({
                        'account_src_id': f'account.{cid}_a7050',
                        'account_dest_id': f'account.{cid}_a7052',
                    }),
                ],
                'tax_ids': [
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-06',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-06-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-12',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-12-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-21',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-21-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-06',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-06-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-12',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-12-ROW-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-21',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-21-ROW-CC',
                    }),
                ]
            },
            f"{cid}_fiscal_position_template_4": {
                'name': _("Régime Cocontractant"),
                'sequence': 5,
                'tax_ids': [
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-L',
                        'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-06',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-06-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-12',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-12-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-21',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-21-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-S',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-G',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-06',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-06-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-12',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-12-CC',
                    }),
                    Command.create({
                        'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-21',
                        'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-21-CC',
                    }),
                ]
            },
        }

    def _get_reconcile_model(self):
        cid = self.env.company.id
        return {
            f"{cid}_escompte_template": {
                'name': _("Escompte"),
                'line_ids': [
                    Command.create({
                        'account_id': f'account.{cid}_a653',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': _("Escompte accordé"),
                    }),
                ],
            },
            f"{cid}_frais_bancaires_htva_template": {
                'name': _("Frais bancaires HTVA"),
                'line_ids': [
                    Command.create({
                        'account_id': f'account.{cid}_a6560',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': _("Frais bancaires HTVA"),
                    }),
                ],
            },
            f"{cid}_frais_bancaires_tva21_template": {
                'name': _("Frais bancaires TVA21"),
                'line_ids': [
                    Command.create({
                        'account_id': f'account.{cid}_a6560',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': _("Frais bancaires TVA21"),
                        'tax_ids': [
                            Command.set([f'account.{cid}_attn_TVA-21-inclus-dans-prix']),
                        ]
                    }),
                ],
            },
            f"{cid}_virements_internes_template": {
                'name': _("Virements internes"),
                'line_ids': [
                    Command.create({
                        'account_id': self.env['account.account'].search([
                            ('code', '=like', self._get_template_data('transfer_account_code_prefix') + '%').id,
                            ('company_id', '=', cid)
                        ]).id,
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': _("Virements internes"),
                    }),
                ],
            },
            f"{cid}_compte_attente_template": {
                'name': _("Compte Attente"),
                'line_ids': [
                    Command.create({
                        'account_id': f'account.{cid}_a499',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': '',
                    }),
                ],
            },
        }

    def _get_account_tax(self):
        cid = self.env.company.id
        if self.env.company.chart_template != 'be':
            return super()._get_account_tax()
        return {
            f'{cid}_attn_VAT-OUT-21-L': {
                'sequence': 10,
                'description': 'TVA 21%',
                'name': '21%',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-21-S': {
                'sequence': 11,
                'description': 'TVA 21%',
                'name': '21% S.',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-12-S': {
                'sequence': 20,
                'description': 'TVA 12%',
                'name': '12% S.',
                'price_include': True,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-12-L': {
                'sequence': 21,
                'description': 'TVA 12%',
                'name': '12%',
                'price_include': True,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-06-S': {
                'sequence': 30,
                'description': 'TVA 6%',
                'name': '6% S.',
                'price_include': True,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-06-L': {
                'sequence': 31,
                'description': 'TVA 6%',
                'name': '6%',
                'price_include': True,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-S': {
                'sequence': 40,
                'description': 'TVA 0%',
                'name': '0% S.',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-L': {
                'sequence': 41,
                'description': 'TVA 0%',
                'name': '0%',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-CC': {
                'sequence': 50,
                'description': 'TVA 0% Cocont.',
                'name': '0% Cocont.',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-EU-S': {
                'sequence': 60,
                'description': 'TVA 0% EU',
                'name': '0% EU S.',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-EU-L': {
                'sequence': 61,
                'description': 'TVA 0% EU',
                'name': '0% EU M.',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-EU-T': {
                'sequence': 62,
                'description': 'TVA 0% EU',
                'name': '0% EU T.',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-ROW': {
                'sequence': 70,
                'description': 'TVA 0% Non EU',
                'name': '0% Non EU',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-21': {
                'sequence': 110,
                'description': 'TVA 21%',
                'name': '21% M.',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-12': {
                'sequence': 120,
                'description': 'TVA 12%',
                'name': '12% M.',
                'price_include': True,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-06': {
                'sequence': 130,
                'description': 'TVA 6%',
                'name': '6% M.',
                'price_include': True,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-00': {
                'sequence': 140,
                'description': 'TVA 0%',
                'name': '0% M.',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_TVA-21-inclus-dans-prix': {
                'sequence': 150,
                'description': 'TVA 21% TTC',
                'name': '21% S. TTC',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-S': {
                'sequence': 210,
                'description': 'TVA 21%',
                'name': '21% S.',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-G': {
                'sequence': 220,
                'description': 'TVA 21%',
                'name': '21% Biens divers',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-S': {
                'sequence': 230,
                'description': 'TVA 12%',
                'name': '12% S.',
                'price_include': True,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-G': {
                'sequence': 240,
                'description': 'TVA 12%',
                'name': '12% Biens divers',
                'price_include': True,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-S': {
                'sequence': 250,
                'description': 'TVA 6%',
                'name': '6% S.',
                'price_include': True,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-G': {
                'sequence': 260,
                'description': 'TVA 6%',
                'name': '6% Biens divers',
                'price_include': True,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-S': {
                'sequence': 270,
                'description': 'TVA 0%',
                'name': '0% S.',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-G': {
                'sequence': 280,
                'description': 'TVA 0%',
                'name': '0% Biens divers',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-21': {
                'sequence': 310,
                'description': 'TVA 21%',
                'name': "21% Biens d'investissement",
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-12': {
                'sequence': 320,
                'description': 'TVA 12%',
                'name': "12% Biens d'investissement",
                'price_include': True,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-06': {
                'sequence': 330,
                'description': 'TVA 6%',
                'name': "6% Biens d'investissement",
                'price_include': True,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-00': {
                'sequence': 340,
                'description': 'TVA 0%',
                'name': "0% Biens d'investissement",
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-21-CC': {
                'sequence': 410,
                'description': 'TVA 21% Cocont.',
                'name': '21% Cocont. M.',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-12-CC': {
                'sequence': 420,
                'description': 'TVA 12% Cocont.',
                'name': '12% Cocont. M.',
                'price_include': True,
                'amount_type': 'percent',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-06-CC': {
                'sequence': 430,
                'description': 'TVA 6% Cocont.',
                'name': '6% Cocont. M.',
                'price_include': True,
                'amount_type': 'percent',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-00-CC': {
                'sequence': 440,
                'description': 'TVA 0% Cocont.',
                'name': '0% Cocont. M.',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-CC': {
                'sequence': 510,
                'description': 'TVA 21% Cocont.',
                'name': '21% Cocont .S.',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-CC': {
                'sequence': 520,
                'description': 'TVA 12% Cocont.',
                'name': '12% Cocont. S.',
                'price_include': True,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-CC': {
                'sequence': 530,
                'description': 'TVA 6% Cocont.',
                'name': '6% Cocont. S.',
                'price_include': True,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-CC': {
                'sequence': 540,
                'description': 'TVA 0% Cocont.',
                'name': '0% Cocont. S.',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-21-CC': {
                'sequence': 610,
                'description': 'TVA 21% Cocont.',
                'name': "21% Cocont. - Biens d'investissement",
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-12-CC': {
                'sequence': 620,
                'description': 'TVA 12% Cocont.',
                'name': "12% Cocont. - Biens d'investissement",
                'price_include': True,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-06-CC': {
                'sequence': 630,
                'description': 'TVA 6% Cocont.',
                'name': "6% Cocont. - Biens d'investissement",
                'price_include': True,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-00-CC': {
                'sequence': 640,
                'description': 'TVA 0% Cocont.',
                'name': "0% Cocont. - Biens d'investissement",
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-CAR-EXC': {
                'sequence': 720,
                'description': 'TVA 50% Non Déductible - Frais de voiture (Prix Excl.)',
                'name': '50% Non Déductible - Frais de voiture (Prix Excl.)',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-21-EU': {
                'sequence': 1110,
                'description': 'TVA 21% EU',
                'name': '21% EU M.',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-12-EU': {
                'sequence': 1120,
                'description': 'TVA 12% EU',
                'name': '12% EU M.',
                'price_include': True,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-06-EU': {
                'sequence': 1130,
                'description': 'TVA 6% EU',
                'name': '6% EU M.',
                'price_include': True,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-00-EU': {
                'sequence': 1140,
                'description': 'TVA 0% EU',
                'name': '0% EU M.',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-EU-S': {
                'sequence': 1210,
                'description': 'TVA 21% EU',
                'name': '21% EU S.',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-EU-G': {
                'sequence': 1220,
                'description': 'TVA 21% EU',
                'name': '21% EU - Biens divers',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-EU-S': {
                'sequence': 1230,
                'description': 'TVA 12% EU',
                'name': '12% EU S.',
                'price_include': True,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-EU-G': {
                'sequence': 1240,
                'description': 'TVA 12% EU',
                'name': '12% EU - Biens divers',
                'price_include': True,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-EU-S': {
                'sequence': 1250,
                'description': 'TVA 6% EU',
                'name': '6% EU S.',
                'price_include': True,
                'amount_type': 'percent',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-EU-G': {
                'sequence': 1260,
                'description': 'TVA 6% EU',
                'name': '6% EU - Biens divers',
                'price_include': True,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-EU-S': {
                'sequence': 1270,
                'description': 'TVA 0% EU',
                'name': '0% EU S.',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-21-EU': {
                'sequence': 1310,
                'description': 'TVA 21% EU',
                'name': "21% EU - Biens d'investissement",
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-EU-G': {
                'sequence': 1280,
                'description': 'TVA 0% EU',
                'name': '0% EU - Biens divers',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-12-EU': {
                'sequence': 1320,
                'description': 'TVA 12% EU',
                'name': "12% EU - Biens d'investissement",
                'price_include': True,
                'amount_type': 'percent',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-06-EU': {
                'sequence': 1330,
                'description': 'TVA 6% EU',
                'name': "6% EU - Biens d'investissement",
                'price_include': True,
                'amount_type': 'percent',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-00-EU': {
                'sequence': 1340,
                'description': 'TVA 0% EU',
                'name': "0% EU - Biens d'investissement",
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-21-ROW-CC': {
                'sequence': 2110,
                'description': 'TVA 21% Non EU',
                'name': '21% Non EU M.',
                'price_include': True,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-12-ROW-CC': {
                'sequence': 2120,
                'description': 'TVA 12% Non EU',
                'name': '12% Non EU M.',
                'amount': 12.0,
                'price_include': True,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-06-ROW-CC': {
                'sequence': 2130,
                'description': 'TVA 6% Non EU',
                'name': '6% Non EU M.',
                'price_include': True,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-00-ROW-CC': {
                'sequence': 2140,
                'description': 'TVA 0% Non EU',
                'name': '0% Non EU M.',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-ROW-CC': {
                'sequence': 2210,
                'description': 'TVA 21% Non EU',
                'name': '21% Non EU S.',
                'amount': 21.0,
                'price_include': True,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-ROW-CC': {
                'sequence': 2220,
                'description': 'TVA 12% Non EU',
                'name': '12% Non EU S.',
                'price_include': True,
                'amount_type': 'percent',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-ROW-CC': {
                'sequence': 2230,
                'description': 'TVA 6% Non EU',
                'name': '6% Non EU S.',
                'price_include': True,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'amount': 6.0,
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-ROW-CC': {
                'sequence': 2240,
                'description': 'TVA 0% Non EU',
                'name': '0% Non EU S.',
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-21-ROW-CC': {
                'sequence': 2310,
                'description': 'TVA 21% Non EU',
                'name': "21% Non EU - Biens d'investissement",
                'amount': 21.0,
                'price_include': True,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-12-ROW-CC': {
                'sequence': 2320,
                'description': 'TVA 12% Non EU',
                'name': "12% Non EU - Biens d'investissement",
                'price_include': True,
                'amount_type': 'percent',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-06-ROW-CC': {
                'sequence': 2330,
                'description': 'TVA 6% Non EU',
                'name': "6% Non EU - Biens d'investissement",
                'price_include': True,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'amount': 6.0,
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-00-ROW-CC': {
                'sequence': 2340,
                'description': 'TVA 0% Non EU',
                'name': "0% Non EU - Biens d'investissement",
                'price_include': True,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': True,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            'l10n_be.tax_report_line_83',
                            'l10n_be.tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            'l10n_be.tax_report_line_85',
                        ],
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
        }
