# -*- coding: utf-8 -*-
import logging
from datetime import date

from odoo import api, models, Command
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self):
        ref = self.env.ref

        # Do not load generic demo data on these companies
        tr_demo_companies = (
            ref('l10n_tr.demo_company_tr', raise_if_not_found=False),
        )
        if self.env.company in tr_demo_companies:
            yield self._get_demo_data_move_tr()

        else:
            for model, data in super()._get_demo_data():
                yield model, data

    @api.model
    def _post_create_demo_data(self, created):
        cid = self.env.company.id
        ref = self.env.ref

        # Do not load generic demo data on these companies
        # We use dedicated demo invoices in order to demonstrate the special
        # feature of this localization
        tr_demo_companies = (
            ref('l10n_tr.demo_company_tr', raise_if_not_found=False),
        )
        if self.env.company not in tr_demo_companies:
            return super()._post_create_demo_data(created)

        if created._name == 'account.move':
            created = created.with_context(check_move_validity=False)
            # This will remove the manually set Fiscal Position on the move because there is a
            # Domestic (standard) FP and an Export ones that one of them will apply. In reality
            # the user first sets the partner, then the FP and finally the lines, we have to do the same
            for move in created:
                move._onchange_partner_id()

            ref(f'l10n_tr.{cid}_demo_invoice_3_tevkifat').fiscal_position_id = ref(f'l10n_tr.{cid}_account_fiscal_position_610')
            ref(f'l10n_tr.{cid}_demo_invoice_4_istisna').fiscal_position_id = ref(f'l10n_tr.{cid}_account_fiscal_position_310')
            ref(f'l10n_tr.{cid}_demo_bill_4_tevkifat').fiscal_position_id = ref(f'l10n_tr.{cid}_account_fiscal_position_610')
            ref(f'l10n_tr.{cid}_demo_bill_6_istisna').fiscal_position_id = ref(f'l10n_tr.{cid}_account_fiscal_position_310')

            created.line_ids._onchange_product_id()
            created.line_ids._onchange_account_id()

            created._recompute_dynamic_lines(
                recompute_all_taxes=True,
                recompute_tax_base_amount=True,
            )

            # the invoice_extract acts like a placeholder for the OCR to be ran and doesn't contain
            # any lines yet

            for move in created.filtered(lambda rec: rec.line_ids):
                try:
                    move.action_post()
                except (UserError, ValidationError):
                    _logger.exception('Error while posting demo data')

    @api.model
    def _get_demo_data_move_tr(self):
        cid = self.env.company.id
        ref = self.env.ref

        return ('account.move', {
            f'l10n_tr.{cid}_demo_invoice_1_domestic': {
                'move_type': 'out_invoice',
                'partner_id': ref('l10n_tr.res_partner_tr_1').id,
                'invoice_user_id': ref('base.user_demo').id,
                'invoice_payment_term_id': ref('account.account_payment_term_immediate').id,
                'invoice_date': date.today().strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.product_delivery_01').id, 'quantity': 5}),
                    Command.create({'product_id': ref('product.product_delivery_02').id, 'quantity': 5}),
                ],
            },
            f'l10n_tr.{cid}_demo_invoice_2_foreign': {
                'move_type': 'out_invoice',
                'partner_id': ref('base.res_partner_2').id,
                'invoice_user_id': False,
                'invoice_date': date.today().strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.product_delivery_01').id, 'quantity': 5}),
                    Command.create({'product_id': ref('product.product_delivery_02').id, 'quantity': 5}),
                ],
            },
            f'l10n_tr.{cid}_demo_invoice_3_tevkifat': {
                'move_type': 'out_invoice',
                'partner_id': ref('l10n_tr.res_partner_tr_1').id,
                'invoice_user_id': False,
                'invoice_date': date.today().strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.product_delivery_01').id, 'quantity': 5}),
                    Command.create({'product_id': ref('product.product_delivery_02').id, 'quantity': 5}),
                ],
            },
            f'l10n_tr.{cid}_demo_invoice_4_istisna': {
                'move_type': 'out_invoice',
                'partner_id': ref('l10n_tr.res_partner_tr_1').id,
                'invoice_user_id': False,
                'invoice_date': date.today().strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.product_delivery_01').id, 'quantity': 5}),
                    Command.create({'product_id': ref('product.product_delivery_02').id, 'quantity': 5}),
                ],
            },
            f'l10n_tr.{cid}_demo_bill_1_domestic': {
                'move_type': 'in_invoice',
                'partner_id': ref('l10n_tr.res_partner_tr_1').id,
                'invoice_user_id': ref('base.user_demo').id,
                'invoice_payment_term_id': ref('account.account_payment_term_immediate').id,
                'invoice_date': date.today().strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create(
                        {'product_id': ref('product.product_delivery_01').id, 'quantity': 5, 'price_unit': 55.0}),
                    Command.create(
                        {'product_id': ref('product.product_delivery_02').id, 'quantity': 5, 'price_unit': 35.0}),
                ],
            },
            f'l10n_tr.{cid}_demo_bill_2_foreign': {
                'move_type': 'in_invoice',
                'partner_id': ref('base.res_partner_2').id,
                'invoice_user_id': False,
                'invoice_date': date.today().strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create(
                        {'product_id': ref('product.product_delivery_01').id, 'quantity': 5, 'price_unit': 55.0}),
                    Command.create(
                        {'product_id': ref('product.product_delivery_02').id, 'quantity': 5, 'price_unit': 35.0}),
                ],
            },
            f'l10n_tr.{cid}_demo_bill_3_foreign_ads': {
                'move_type': 'in_invoice',
                'partner_id': ref('base.res_partner_2').id,
                'invoice_user_id': False,
                'invoice_date': date.today().strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create(
                        {'product_id': ref('l10n_tr.product_foreign_ads').id, 'quantity': 5, 'price_unit': 100.0}),
                ],
            },
            f'l10n_tr.{cid}_demo_bill_4_tevkifat': {
                'move_type': 'in_invoice',
                'partner_id': ref('base.res_partner_3').id,
                'invoice_user_id': False,
                'invoice_date': date.today().strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create(
                        {'product_id': ref('product.product_delivery_01').id, 'quantity': 5, 'price_unit': 55.0}),
                    Command.create(
                        {'product_id': ref('product.product_delivery_02').id, 'quantity': 5, 'price_unit': 35.0}),
                ],
            },
            f'l10n_tr.{cid}_demo_bill_5_tevkifat': {
                'move_type': 'in_invoice',
                'partner_id': ref('l10n_tr.res_partner_tr_1').id,
                'invoice_user_id': False,
                'invoice_date': date.today().strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create(
                        {'product_id': ref('l10n_tr.product_domestic_ads').id, 'quantity': 5, 'price_unit': 100.0}),
                ],
            },
            f'l10n_tr.{cid}_demo_bill_6_istisna': {
                'move_type': 'in_invoice',
                'partner_id': ref('l10n_tr.res_partner_tr_1').id,
                'invoice_user_id': False,
                'invoice_date': date.today().strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create(
                        {'product_id': ref('product.product_delivery_01').id, 'quantity': 5, 'price_unit': 55.0}),
                    Command.create(
                        {'product_id': ref('product.product_delivery_02').id, 'quantity': 5, 'price_unit': 35.0}),
                ],
            },
        })
