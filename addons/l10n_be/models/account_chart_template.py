# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _get_be_chart_template_data(self, template_code, company):
        res = self._get_chart_template_data(company)
        if template_code == 'be':
            res['account.fiscal.position'] = self._get_be_fiscal_position(template_code, company)
            res['account.reconcile.model'] = self._get_be_reconcile_model(template_code, company)
            res['account.reconcile.model.line'] = self._get_be_reconcile_model_line(template_code, company)
            res['account.fiscal.position.tax'] = self._get_be_fiscal_position_tax(template_code, company)
        return res

    def _get_be_template_data(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            'l10nbe_chart_template': {
                'bank_account_code_prefix': '550',
                'cash_account_code_prefix': '570',
                'transfer_account_code_prefix': '580',
                'spoken_languages': 'nl_BE;nl_NL;fr_FR;fr_BE;de_DE',
                'code_digits': '6',
                'property_account_receivable_id': f'account.{cid}_a400',
                'property_account_payable_id': f'account.{cid}_a440',
                'property_account_expense_categ_id': f'account.{cid}_a600',
                'property_account_income_categ_id': f'account.{cid}_a7000',
                'property_tax_payable_account_id': f'account.{cid}_a4512',
                'property_tax_receivable_account_id': f'account.{cid}_a4112',
                'account_journal_suspense_account_id': f'account.{cid}_a499',
            }
,
        }

    def _get_be_account_tax(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_attn_VAT-OUT-21-L': {
                'sequence': 10,
                'description': 'TVA 21%',
                'name': '21%',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_03',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_54',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_49',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_64',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-21-S': {
                'sequence': 11,
                'description': 'TVA 21%',
                'name': '21% S.',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_03',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_54',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_49',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_64',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-12-S': {
                'sequence': 20,
                'description': 'TVA 12%',
                'name': '12% S.',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_02',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_54',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_49',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_64',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-12-L': {
                'sequence': 21,
                'description': 'TVA 12%',
                'name': '12%',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_02',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_54',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_49',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_64',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-06-S': {
                'sequence': 30,
                'description': 'TVA 6%',
                'name': '6% S.',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_01',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_54',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_49',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_64',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-06-L': {
                'sequence': 31,
                'description': 'TVA 6%',
                'name': '6%',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_01',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_54',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_49',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_64',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-S': {
                'sequence': 40,
                'description': 'TVA 0%',
                'name': '0% S.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_00',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_49',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-L': {
                'sequence': 41,
                'description': 'TVA 0%',
                'name': '0%',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_00',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_49',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-CC': {
                'sequence': 50,
                'description': 'TVA 0% Cocont.',
                'name': '0% Cocont.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_45',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_49',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-EU-S': {
                'sequence': 60,
                'description': 'TVA 0% EU',
                'name': '0% EU S.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_44',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_48s44',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-EU-L': {
                'sequence': 61,
                'description': 'TVA 0% EU',
                'name': '0% EU M.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_46L',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_48s46L',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-EU-T': {
                'sequence': 62,
                'description': 'TVA 0% EU',
                'name': '0% EU T.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_46T',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_48s46T',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-OUT-00-ROW': {
                'sequence': 70,
                'description': 'TVA 0% Non EU',
                'name': '0% Non EU',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_47',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_49',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-21': {
                'sequence': 110,
                'description': 'TVA 21%',
                'name': '21% M.',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-12': {
                'sequence': 120,
                'description': 'TVA 12%',
                'name': '12% M.',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-06': {
                'sequence': 130,
                'description': 'TVA 6%',
                'name': '6% M.',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-00': {
                'sequence': 140,
                'description': 'TVA 0%',
                'name': '0% M.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
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
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-S': {
                'sequence': 210,
                'description': 'TVA 21%',
                'name': '21% S.',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-G': {
                'sequence': 220,
                'description': 'TVA 21%',
                'name': '21% Biens divers',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-S': {
                'sequence': 230,
                'description': 'TVA 12%',
                'name': '12% S.',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-G': {
                'sequence': 240,
                'description': 'TVA 12%',
                'name': '12% Biens divers',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-S': {
                'sequence': 250,
                'description': 'TVA 6%',
                'name': '6% S.',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-G': {
                'sequence': 260,
                'description': 'TVA 6%',
                'name': '6% Biens divers',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-S': {
                'sequence': 270,
                'description': 'TVA 0%',
                'name': '0% S.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-G': {
                'sequence': 280,
                'description': 'TVA 0%',
                'name': '0% Biens divers',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-21': {
                'sequence': 310,
                'description': 'TVA 21%',
                'name': "21% Biens d'investissement",
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-12': {
                'sequence': 320,
                'description': 'TVA 12%',
                'name': "12% Biens d'investissement",
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-06': {
                'sequence': 330,
                'description': 'TVA 6%',
                'name': "6% Biens d'investissement",
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-00': {
                'sequence': 340,
                'description': 'TVA 0%',
                'name': "0% Biens d'investissement",
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-21-CC': {
                'sequence': 410,
                'description': 'TVA 21% Cocont.',
                'name': '21% Cocont. M.',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_56',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-12-CC': {
                'sequence': 420,
                'description': 'TVA 12% Cocont.',
                'name': '12% Cocont. M.',
                'price_include': False,
                'amount_type': 'percent',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_56',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-06-CC': {
                'sequence': 430,
                'description': 'TVA 6% Cocont.',
                'name': '6% Cocont. M.',
                'price_include': False,
                'amount_type': 'percent',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_56',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-00-CC': {
                'sequence': 440,
                'description': 'TVA 0% Cocont.',
                'name': '0% Cocont. M.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-CC': {
                'sequence': 510,
                'description': 'TVA 21% Cocont.',
                'name': '21% Cocont .S.',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_56',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-CC': {
                'sequence': 520,
                'description': 'TVA 12% Cocont.',
                'name': '12% Cocont. S.',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_56',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-CC': {
                'sequence': 530,
                'description': 'TVA 6% Cocont.',
                'name': '6% Cocont. S.',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_56',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-CC': {
                'sequence': 540,
                'description': 'TVA 0% Cocont.',
                'name': '0% Cocont. S.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-21-CC': {
                'sequence': 610,
                'description': 'TVA 21% Cocont.',
                'name': "21% Cocont. - Biens d'investissement",
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_56',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-12-CC': {
                'sequence': 620,
                'description': 'TVA 12% Cocont.',
                'name': "12% Cocont. - Biens d'investissement",
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_56',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-06-CC': {
                'sequence': 630,
                'description': 'TVA 6% Cocont.',
                'name': "6% Cocont. - Biens d'investissement",
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_56',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451056',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-00-CC': {
                'sequence': 640,
                'description': 'TVA 0% Cocont.',
                'name': "0% Cocont. - Biens d'investissement",
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-CAR-EXC': {
                'sequence': 720,
                'description': 'TVA 50% Non Déductible - Frais de voiture (Prix Excl.)',
                'name': '50% Non Déductible - Frais de voiture (Prix Excl.)',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 50,
                        'repartition_type': 'tax',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 50,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 50,
                        'repartition_type': 'tax',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 50,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_63',
                        ],
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-21-EU': {
                'sequence': 1110,
                'description': 'TVA 21% EU',
                'name': '21% EU M.',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_86',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_55',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_86',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-12-EU': {
                'sequence': 1120,
                'description': 'TVA 12% EU',
                'name': '12% EU M.',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_86',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_55',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_86',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-06-EU': {
                'sequence': 1130,
                'description': 'TVA 6% EU',
                'name': '6% EU M.',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_86',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_55',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_86',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-00-EU': {
                'sequence': 1140,
                'description': 'TVA 0% EU',
                'name': '0% EU M.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_86',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_86',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-EU-S': {
                'sequence': 1210,
                'description': 'TVA 21% EU',
                'name': '21% EU S.',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_88',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_55',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_88',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-21-EU-G': {
                'sequence': 1220,
                'description': 'TVA 21% EU',
                'name': '21% EU - Biens divers',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_86',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_55',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_86',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-EU-S': {
                'sequence': 1230,
                'description': 'TVA 12% EU',
                'name': '12% EU S.',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_88',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_55',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_88',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-EU-G': {
                'sequence': 1240,
                'description': 'TVA 12% EU',
                'name': '12% EU - Biens divers',
                'price_include': False,
                'amount': 12.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_86',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_55',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_86',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-EU-S': {
                'sequence': 1250,
                'description': 'TVA 6% EU',
                'name': '6% EU S.',
                'price_include': False,
                'amount_type': 'percent',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_88',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_55',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_88',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-EU-G': {
                'sequence': 1260,
                'description': 'TVA 6% EU',
                'name': '6% EU - Biens divers',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_86',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_55',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_86',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-EU-S': {
                'sequence': 1270,
                'description': 'TVA 0% EU',
                'name': '0% EU S.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_88',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_88',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-21-EU': {
                'sequence': 1310,
                'description': 'TVA 21% EU',
                'name': "21% EU - Biens d'investissement",
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_86',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_55',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_86',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-EU-G': {
                'sequence': 1280,
                'description': 'TVA 0% EU',
                'name': '0% EU - Biens divers',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_86',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_86',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-12-EU': {
                'sequence': 1320,
                'description': 'TVA 12% EU',
                'name': "12% EU - Biens d'investissement",
                'price_include': False,
                'amount_type': 'percent',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_86',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_55',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_86',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-06-EU': {
                'sequence': 1330,
                'description': 'TVA 6% EU',
                'name': "6% EU - Biens d'investissement",
                'price_include': False,
                'amount_type': 'percent',
                'amount': 6.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_86',
                        ],
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_55',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_86',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451055',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-00-EU': {
                'sequence': 1340,
                'description': 'TVA 0% EU',
                'name': "0% EU - Biens d'investissement",
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_86',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_86',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_84',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-21-ROW-CC': {
                'sequence': 2110,
                'description': 'TVA 21% Non EU',
                'name': '21% Non EU M.',
                'price_include': False,
                'amount': 21.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_57',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-12-ROW-CC': {
                'sequence': 2120,
                'description': 'TVA 12% Non EU',
                'name': '12% Non EU M.',
                'amount': 12.0,
                'price_include': False,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_57',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-06-ROW-CC': {
                'sequence': 2130,
                'description': 'TVA 6% Non EU',
                'name': '6% Non EU M.',
                'price_include': False,
                'amount': 6.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_57',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V81-00-ROW-CC': {
                'sequence': 2140,
                'description': 'TVA 0% Non EU',
                'name': '0% Non EU M.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_81',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
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
                'price_include': False,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_57',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-12-ROW-CC': {
                'sequence': 2220,
                'description': 'TVA 12% Non EU',
                'name': '12% Non EU S.',
                'price_include': False,
                'amount_type': 'percent',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_57',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-06-ROW-CC': {
                'sequence': 2230,
                'description': 'TVA 6% Non EU',
                'name': '6% Non EU S.',
                'price_include': False,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'amount': 6.0,
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_57',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V82-00-ROW-CC': {
                'sequence': 2240,
                'description': 'TVA 0% Non EU',
                'name': '0% Non EU S.',
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_82',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
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
                'price_include': False,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_21',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_57',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-12-ROW-CC': {
                'sequence': 2320,
                'description': 'TVA 12% Non EU',
                'name': "12% Non EU - Biens d'investissement",
                'price_include': False,
                'amount_type': 'percent',
                'amount': 12.0,
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_12',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_57',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-06-ROW-CC': {
                'sequence': 2330,
                'description': 'TVA 6% Non EU',
                'name': "6% Non EU - Biens d'investissement",
                'price_include': False,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'amount': 6.0,
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_6',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_59',
                        ],
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_57',
                        ],
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a411',
                    }),
                    Command.set({
                        'factor_percent': -100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_a451057',
                    }),
                ],
            },
            f'{cid}_attn_VAT-IN-V83-00-ROW-CC': {
                'sequence': 2340,
                'description': 'TVA 0% Non EU',
                'name': "0% Non EU - Biens d'investissement",
                'price_include': False,
                'amount': 0.0,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'active': False,
                'tax_group_id': f'account.{cid}_tax_group_tva_0',
                'invoice_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.clear(),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'minus_report_line_ids': [
                            f'account.{cid}_tax_report_line_83',
                            f'account.{cid}_tax_report_line_87',
                        ],
                        'plus_report_line_ids': [
                            f'account.{cid}_tax_report_line_85',
                        ],
                    }),
                    Command.set({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            }
        }

    def _get_be_res_company(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'base.company_{cid}': {
                'currency_id': 'base.EUR',
                'account_fiscal_country_id': 'base.be',
                'account_default_pos_receivable_account_id': f'account.{cid}_a4001',
                'income_currency_exchange_account_id': f'account.{cid}_a754',
                'expense_currency_exchange_account_id': f'account.{cid}_a654',
            }
,
        }

    def _get_be_fiscal_position(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_fiscal_position_template_1': {
                'sequence': 1,
                'name': 'Régime National',
                'auto_apply': 1,
                'vat_required': 1,
                'country_id': 'base.be',
            },
            f'{cid}_fiscal_position_template_5': {
                'sequence': 2,
                'name': 'EU privé',
                'auto_apply': 1,
                'country_group_id': 'base.europe',
            },
            f'{cid}_fiscal_position_template_2': {
                'sequence': 4,
                'name': 'Régime Extra-Communautaire',
                'auto_apply': 1,
            },
            f'{cid}_fiscal_position_template_3': {
                'sequence': 3,
                'name': 'Régime Intra-Communautaire',
                'auto_apply': 1,
                'vat_required': 1,
                'country_group_id': 'base.europe',
            },
            f'{cid}_fiscal_position_template_4': {
                'name': 'Régime Cocontractant',
                'sequence': 5,
            }
        }

    def _get_be_reconcile_model(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_escompte_template': {
                'name': 'Escompte',
            },
            f'{cid}_frais_bancaires_htva_template': {
                'name': 'Frais bancaires HTVA',
            },
            f'{cid}_frais_bancaires_tva21_template': {
                'name': 'Frais bancaires TVA21',
            },
            f'{cid}_virements_internes_template': {
                'name': 'Virements internes',
                'to_check': False,
            },
            f'{cid}_compte_attente_template': {
                'name': 'Compte Attente',
                'to_check': True,
            }
        }

    def _get_be_reconcile_model_line(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_escompte_line_template': {
                'model_id': 'l10n_be.escompte_template',
                'account_id': 'a653',
                'amount_type': 'percentage',
                'amount_string': '100',
                'label': 'Escompte accordé',
            },
            f'{cid}_frais_bancaires_htva_line_template': {
                'model_id': 'l10n_be.frais_bancaires_htva_template',
                'account_id': 'a6560',
                'amount_type': 'percentage',
                'amount_string': '100',
                'label': 'Frais bancaires HTVA',
            },
            f'{cid}_frais_bancaires_tva21_line_template': {
                'model_id': 'l10n_be.frais_bancaires_tva21_template',
                'account_id': 'a6560',
                'amount_type': 'percentage',
                'tax_ids': [
                    Command.clear([
                        'l10n_be.attn_TVA-21-inclus-dans-prix',
                    ]),
                ],
                'amount_string': '100',
                'label': 'Frais bancaires TVA21',
            },
            f'{cid}_virements_internes_line_template': {
                'model_id': 'l10n_be.virements_internes_template',
                'account_id': None,
                'amount_type': 'percentage',
                'amount_string': '100',
                'label': 'Virements internes',
            },
            f'{cid}_compte_attente_line_template': {
                'model_id': 'l10n_be.compte_attente_template',
                'account_id': 'a499',
                'amount_type': 'percentage',
                'amount_string': '100',
                'label': None,
            }
        }

    def _get_be_fiscal_position_tax(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f'{cid}_afpttn_intracom_1': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
            },
            f'{cid}_afpttn_intracom_2': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
            },
            f'{cid}_afpttn_intracom_3': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
            },
            f'{cid}_afpttn_intracom_4': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
            },
            f'{cid}_afpttn_intracom_5': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
            },
            f'{cid}_afpttn_intracom_6': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
            },
            f'{cid}_afpttn_intracom_7': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-S',
            },
            f'{cid}_afpttn_intracom_8': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-EU-L',
            },
            f'{cid}_afpttn_intracom_9': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-00',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-00-EU',
            },
            f'{cid}_afpttn_intracom_10': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-06',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-06-EU',
            },
            f'{cid}_afpttn_intracom_11': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-12',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-12-EU',
            },
            f'{cid}_afpttn_intracom_12': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-21',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-21-EU',
            },
            f'{cid}_afpttn_intracom_13': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-00-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-00-EU-S',
            },
            f'{cid}_afpttn_intracom_14': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-00-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-00-EU-G',
            },
            f'{cid}_afpttn_intracom_15': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-EU-S',
            },
            f'{cid}_afpttn_intracom_16': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-EU-G',
            },
            f'{cid}_afpttn_intracom_17': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-EU-S',
            },
            f'{cid}_afpttn_intracom_18': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-EU-G',
            },
            f'{cid}_afpttn_intracom_19': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-EU-S',
            },
            f'{cid}_afpttn_intracom_20': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-EU-G',
            },
            f'{cid}_afpttn_intracom_21': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-00',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-00-EU',
            },
            f'{cid}_afpttn_intracom_22': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-06',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-06-EU',
            },
            f'{cid}_afpttn_intracom_23': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-12',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-12-EU',
            },
            f'{cid}_afpttn_intracom_24': {
                'position_id': f'account.{cid}_fiscal_position_template_3',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-21',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-21-EU',
            },
            f'{cid}_afpttn_extracom_1': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_2': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_3': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_4': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_5': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_6': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_7': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_8': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-ROW',
            },
            f'{cid}_afpttn_extracom_9': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-06',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-06-ROW-CC',
            },
            f'{cid}_afpttn_extracom_10': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-12',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-12-ROW-CC',
            },
            f'{cid}_afpttn_extracom_11': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-21',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-21-ROW-CC',
            },
            f'{cid}_afpttn_extracom_12': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-ROW-CC',
            },
            f'{cid}_afpttn_extracom_13': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-ROW-CC',
            },
            f'{cid}_afpttn_extracom_14': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-ROW-CC',
            },
            f'{cid}_afpttn_extracom_15': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-ROW-CC',
            },
            f'{cid}_afpttn_extracom_16': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-ROW-CC',
            },
            f'{cid}_afpttn_extracom_17': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-ROW-CC',
            },
            f'{cid}_afpttn_extracom_18': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-06',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-06-ROW-CC',
            },
            f'{cid}_afpttn_extracom_19': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-12',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-12-ROW-CC',
            },
            f'{cid}_afpttn_extracom_20': {
                'position_id': f'account.{cid}_fiscal_position_template_2',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-21',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-21-ROW-CC',
            },
            f'{cid}_afpttn_cocontractant_1': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_2': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-00-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_3': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_4': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-06-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_5': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_6': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-12-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_7': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_8': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-OUT-21-L',
                'tax_dest_id': f'account.{cid}_attn_VAT-OUT-00-CC',
            },
            f'{cid}_afpttn_cocontractant_9': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-06',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-06-CC',
            },
            f'{cid}_afpttn_cocontractant_10': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-12',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-12-CC',
            },
            f'{cid}_afpttn_cocontractant_11': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V81-21',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V81-21-CC',
            },
            f'{cid}_afpttn_cocontractant_12': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-CC',
            },
            f'{cid}_afpttn_cocontractant_13': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-06-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-06-CC',
            },
            f'{cid}_afpttn_cocontractant_14': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-CC',
            },
            f'{cid}_afpttn_cocontractant_15': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-12-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-12-CC',
            },
            f'{cid}_afpttn_cocontractant_16': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-S',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-CC',
            },
            f'{cid}_afpttn_cocontractant_17': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V82-21-G',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V82-21-CC',
            },
            f'{cid}_afpttn_cocontractant_18': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-06',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-06-CC',
            },
            f'{cid}_afpttn_cocontractant_19': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-12',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-12-CC',
            },
            f'{cid}_afpttn_cocontractant_20': {
                'position_id': f'account.{cid}_fiscal_position_template_4',
                'tax_src_id': f'account.{cid}_attn_VAT-IN-V83-21',
                'tax_dest_id': f'account.{cid}_attn_VAT-IN-V83-21-CC',
            }
        }
