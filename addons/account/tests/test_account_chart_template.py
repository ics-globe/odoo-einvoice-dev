# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import collections
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.account.models.chart_template import TEMPLATES


@tagged('post_install', '-at_install')
class AccountChartTemplateTest(TransactionCase):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super(AccountChartTemplateTest, cls).setUpClass()

        # Create user.
        user = cls.env['res.users'].create({
            'name': 'Because I am accountman!',
            'login': 'accountman',
            'password': 'accountman',
            'groups_id': [(6, 0, cls.env.user.groups_id.ids), (4, cls.env.ref('account.group_account_user').id)],
        })
        user.partner_id.email = 'accountman@test.com'

        # Shadow the current environment/cursor with one having the report user.
        # This is mandatory to test access rights.
        cls.env = cls.env(user=user)
        cls.cr = cls.env.cr
        cls.company = cls.env['res.company'].create({'name': "company_1"})
        cls.env.user.company_ids |= cls.company

        cls.AccountChartTemplate = cls.env['account.chart.template']
        cls._prepare_subclasses()

    @classmethod
    def _prepare_subclasses(cls):
        pattern = re.compile(f"^_get_(?P<template_code>{'|'.join(TEMPLATES)})_(?P<model>.*)$")
        matcher = lambda x: re.match(pattern, x)
        attrs = [x for x in dir(cls.AccountChartTemplate)]
        attrs = filter(matcher, attrs)
        attrs = [getattr(cls.AccountChartTemplate, x) for x in attrs]
        get_methods = [x for x in filter(callable, attrs)]
        cls.chart_templates = collections.defaultdict(dict)
        for get_method in get_methods:
            template_code, model = matcher(get_method.__name__).groups()
            cls.chart_templates[template_code][model] = get_method

    def _test_chart_function(self, model, must_be_present):

        def check(template_code, data, _id=None):
            self.assertTrue(isinstance(data, dict))
            for attr in must_be_present:
                message = (
                    f"AccountChartTemplate({template_code}): Function '_get_{template_code}_{model}'"
                    f"does not output '{attr}'{' id=' + _id if _id else ''}"
                )
                self.assertTrue(attr in data, message)

        for template_code, methods in self.chart_templates.items():
            method = methods.get(model, getattr(self.AccountChartTemplate, f"_get_{model}"))
            datas = method(self.AccountChartTemplate, self.company)
            if model == 'template_data':
                return check(template_code, datas)
            self.assertTrue(isinstance(datas, dict))
            for _id, data in datas.items():
                self.assertTrue(bool(_id) and bool(data))
                check(template_code, data, _id)

    def test_default_chart_code(self):
        self.assertEqual('generic_coa', self.AccountChartTemplate._guess_chart_template(self.company))

    def test_country_chart_code(self):
        self.company.country_id = self.env.ref('base.be')
        self.assertEqual('be', self.AccountChartTemplate._guess_chart_template(self.company))

    def test_res_company(self):
        self._test_chart_function("res_company", [
            "account_fiscal_country_id",
            "account_default_pos_receivable_account_id",
            "income_currency_exchange_account_id",
            "expense_currency_exchange_account_id"
        ])

    def test_account_journal(self):
        self._test_chart_function("template_data", [
            'cash_account_code_prefix',
            'bank_account_code_prefix',
            'transfer_account_code_prefix',
            'property_account_receivable_id',
            'property_account_payable_id',
            'property_account_expense_categ_id',
            'property_account_income_categ_id',
            'property_tax_payable_account_id',
            'property_tax_receivable_account_id',
        ])
