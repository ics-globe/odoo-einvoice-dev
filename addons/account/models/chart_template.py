# -*- coding: utf-8 -*-

from odoo import models, _, Command, api, SUPERUSER_ID
from odoo.modules import get_resource_path
from odoo.addons.base.models.ir_translation import IrTranslationImport
import csv
import ast
from collections import defaultdict

import logging

_logger = logging.getLogger(__name__)

TEMPLATES = [
    ('generic_coa', 'Generic Chart Template', None, []),
    ('be', 'BE Belgian PCMN', 'base.be', ['l10n_be']),
    ('fr', 'FR', 'base.fr', ['l10n_fr']),
    ('ch', 'CH', 'base.ch', ['l10n_ch']),
    ('de', 'DE', 'base.de', ['l10n_de']),
]
MODULES = {ct: modules for ct, string, country, modules in TEMPLATES}
COUNTRIES = {country: ct for ct, string, country, modules in TEMPLATES}


def migrate_set_tags_and_taxes_updatable(cr, registry, module):
    ''' This is a utility function used to manually set the flag noupdate to False on tags and account tax templates on localization modules
    that need migration (for example in case of VAT report improvements)
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})
    xml_record_ids = env['ir.model.data'].search([
        ('model', 'in', ['account.tax.template', 'account.account.tag']),
        ('module', 'like', module)
    ]).ids
    if xml_record_ids:
        cr.execute("update ir_model_data set noupdate = 'f' where id in %s", (tuple(xml_record_ids),))

def preserve_existing_tags_on_taxes(cr, registry, module):
    ''' This is a utility function used to preserve existing previous tags during upgrade of the module.'''
    env = api.Environment(cr, SUPERUSER_ID, {})
    xml_records = env['ir.model.data'].search([('model', '=', 'account.account.tag'), ('module', 'like', module)])
    if xml_records:
        cr.execute("update ir_model_data set noupdate = 't' where id in %s", [tuple(xml_records.ids)])

def delegate_to_super_if_code_doesnt_match(class_code):
    """
        This helper decorator helps build localized subclasses which methods
        are only used if the template_code matches their _code, otherwise it delegates
        to the next superclass in the chain.
        If the company argument is empty, it is defaulted with self.env.company
    """
    def wrapper(f):
        def wrapper_inner(*args, **kwargs):
            self, template_code, company, *rest = args
            if template_code != class_code:
                super_method = getattr(super(type(self), self), f.__name__)
                return super_method(template_code, company, **kwargs)
            else:
                if not company:
                    company = self.env.company
                return f(self, template_code, company, *rest, **kwargs)
        return wrapper_inner

    return wrapper


class AccountChartTemplate(models.AbstractModel):
    _name = "account.chart.template"
    _description = "Account Chart Template"

    def _select_chart_template(self, company=False):
        company = company or self.env.company
        result = [(ct, string) for ct, string, country, modules in TEMPLATES]
        if self:
            proposed = self._guess_chart_template(company)
            result.sort(key=lambda sel: (sel[0] != proposed, sel[1]))
        return result

    def _guess_chart_template(self, company=False):
        company = company or self.env.company
        if not company.country_id:
            return 'generic_coa'
        return COUNTRIES.get(company.country_id.get_metadata()[0]['xmlid'], 'generic_coa')

    def try_loading(self, template_code=False, company=False, install_demo=True):
        """ Installs this chart of accounts for the current company if not chart
        of accounts had been created for it yet.

        :param template_code (str): code of the chart template to be loaded.
        :param company (Model<res.company>): the company we try to load the chart template on.
            If not provided, it is retrieved from the context.
        :param install_demo (bool): whether or not we should load demo data right after loading the
            chart template.
        """
        company = company or self.env.company
        template_code = template_code or self._guess_chart_template(company)

        module_ids = self.env['ir.module.module'].search([('name', 'in', MODULES.get(template_code)), ('state', '=', 'uninstalled')])
        if module_ids:
            module_ids.sudo().button_immediate_install()
            self.env.reset()

        with_company = self.sudo().with_context(default_company_id=company.id, allowed_company_ids=[company.id])
        # If we don't have any chart of account on this company, install this chart of account
        if not company.existing_accounting():
            xml_id = company.get_metadata()[0]['xmlid']
            if not xml_id:
                xml_id = f"base.company_{company.id}"
                with_company.env['ir.model.data']._update_xmlids([{'xml_id': xml_id, 'record': self}])
            data = with_company._get_chart_template_data(template_code, company)
            with_company._load_data(data)
            with_company._post_load_data(template_code, company)
            company.flush()
            with_company.env.cache.invalidate()
            # Install the demo data when the first localization is instanciated on the company
            if install_demo and with_company.env.ref('base.module_account').demo:
                try:
                    with with_company.env.cr.savepoint():
                        with_company._load_data(with_company._get_demo_data(company))
                        with_company._post_load_demo_data(company)
                except Exception:
                    # Do not rollback installation of CoA if demo data failed
                    _logger.exception('Error while loading accounting demo data')

    def _load_data(self, data):
        def deref(values, model):
            for field, value in values.items():
                if field not in model._fields:
                    continue
                if model._fields[field].type in ('many2one', 'integer', 'many2one_reference') and isinstance(value, str):
                    values[field] = self.env.ref(value).id
                elif model._fields[field].type in ('one2many', 'many2many'):
                    if value and isinstance(value[0], (list, tuple)):
                        for command in value:
                            if command[0] in (Command.CREATE, Command.UPDATE):
                                deref(command[2], self.env[model._fields[field].comodel_name])
                            if command[0] == Command.SET:
                                for i, value in enumerate(command[2]):
                                    if isinstance(value, str):
                                        command[2][i] = self.env.ref(value).id
            return values

        def defer(all_data):
            created_models = set()
            while all_data:
                (model, data), *all_data = all_data
                created_models.add(model)
                to_delay = defaultdict(dict)
                for xml_id, vals in data.items():
                    for field_name in vals:
                        field = self.env[model]._fields.get(field_name, None)
                        if (field and
                            field.relational and
                            field.comodel_name not in created_models and
                            field.comodel_name in dict(all_data)):
                            to_delay[xml_id][field_name] = vals.pop(field_name)
                if any(to_delay.values()):
                    all_data.append((model, to_delay))
                yield model, data

        irt_cursor = IrTranslationImport(self._cr, True)
        for model, data in defer(list(data.items())):
            translate_vals = defaultdict(list)
            create_vals = []
            for xml_id, record in data.items():
                xml_id = "account.%s" % xml_id if '.' not in xml_id else xml_id
                for translate, value in list(record.items()):
                    if '@' in translate:
                        if value:
                            field, lang = translate.split('@')
                            translate_vals[xml_id].append({
                                'type': 'model',
                                'name': f'{model},{field}',
                                'lang': lang,
                                'src': record[field],
                                'value': value,
                                'comments': None,
                                'imd_model': model,
                                'imd_name': xml_id,
                                'module': 'account',
                            })
                        del record[translate]
                create_vals.append({
                    'xml_id': xml_id,
                    'values': deref(record, self.env[model]),
                    'noupdate': True,
                })
            _logger.info('Loading model %s', model)
            created = self.env[model].sudo()._load_records(create_vals)
            _logger.info('Loaded model %s', model)
            for vals, record in zip(create_vals, created):
                for translation in translate_vals[vals['xml_id']]:
                    irt_cursor.push({**translation, 'res_id': record.id})
        irt_cursor.finish()

    def _load_csv(self, module, company, file_name, post_sanitize=None):
        cid = (company or self.env.company).id
        Model = self.env[".".join(file_name.split(".")[:-1])]
        model_fields = Model._fields
        path_parts = [x for x in ('account', 'data', 'template', module, file_name) if x]
        # Should the path be False then open(False, 'r') will open STDIN for reading
        path = get_resource_path(*path_parts) or ''

        def basic_sanitize_csv(row):
            return {
                key: (
                    value if '@' in key
                    else ast.literal_eval(value) if model_fields[key].type in ('boolean', 'int', 'float')
                    else (value and Model.env.ref(value).id or False) if model_fields[key].type == 'many2one'
                    else (value and Model.env.ref(value).ids or []) if model_fields[key].type in ('one2many', 'many2many')
                    else value
                )
                for key, value in ((key.replace('/id', ''), value) for key, value in row.items())
                if key != 'id'
            }

        if not post_sanitize:
            sanitize_csv = basic_sanitize_csv
        else:
            def sanitize_csv(row):
                return post_sanitize(basic_sanitize_csv(row))

        try:
            with open(path, 'r', encoding="utf-8") as csv_file:
                _logger.info('loading %s', '/'.join(path_parts))
                return {f"{cid}_{row['id']}": sanitize_csv(row) for row in csv.DictReader(csv_file)}
        except OSError as e:
            if path:
                _logger.info("Error reading CSV file %s: %s", path, e)
            else:
                _logger.info("No file %s found for template '%s'", file_name, module)
            return {}

    def _get_chart_template_data(self, template_code, company):
        company = company or self.env.company
        return {
            'account.account': self._get_account_account(template_code, company),
            'account.group': self._get_account_group(template_code, company),
            'account.journal': self._get_account_journal(template_code, company),
            'res.company': self._get_res_company(template_code, company),
            'account.tax.group': self._get_tax_group(template_code, company),
            'account.tax': self._get_account_tax(template_code, company),
        }

    def _get_account_account(self, template_code, company):
        return self._load_csv(template_code, company, 'account.account.csv')

    def _get_account_group(self, template_code, company):
        def account_group_sanitize(row):
            start, end = row['code_prefix_start'], row['code_prefix_end']
            if not end or end < start:
                row['code_prefix_end'] = start
            return row
        return self._load_csv(template_code, company, 'account.group.csv', post_sanitize=account_group_sanitize)

    def _get_tax_group(self, template_code, company):
        return self._load_csv(template_code, company, 'account.tax.group.csv')

    def _post_load_data(self, template_code, company):
        company = (company or self.env.company)
        cid = company.id
        ref = self.env.ref
        template_data = self._get_template_data(template_code, company)
        code_digits = template_data.get('code_digits', 6)
        # Set default cash difference account on company
        if not company.account_journal_suspense_account_id:
            company.account_journal_suspense_account_id = self.env['account.account'].create({
                'name': _("Bank Suspense Account"),
                'code': self.env['account.account']._search_new_account_code(company, code_digits, company.bank_account_code_prefix or ''),
                'user_type_id': self.env.ref('account.data_account_type_current_liabilities').id,
                'company_id': cid,
            })

        account_type_current_assets = self.env.ref('account.data_account_type_current_assets')
        if not company.account_journal_payment_debit_account_id:
            company.account_journal_payment_debit_account_id = self.env['account.account'].create({
                'name': _("Outstanding Receipts"),
                'code': self.env['account.account']._search_new_account_code(company, code_digits, company.bank_account_code_prefix or ''),
                'reconcile': True,
                'user_type_id': account_type_current_assets.id,
                'company_id': cid,
            })

        if not company.account_journal_payment_credit_account_id:
            company.account_journal_payment_credit_account_id = self.env['account.account'].create({
                'name': _("Outstanding Payments"),
                'code': self.env['account.account']._search_new_account_code(company, code_digits, company.bank_account_code_prefix or ''),
                'reconcile': True,
                'user_type_id': account_type_current_assets.id,
                'company_id': cid,
            })

        if not company.default_cash_difference_expense_account_id:
            company.default_cash_difference_expense_account_id = self.env['account.account'].create({
                'name': _('Cash Difference Loss'),
                'code': self.env['account.account']._search_new_account_code(company, code_digits, '999'),
                'user_type_id': self.env.ref('account.data_account_type_expenses').id,
                'tag_ids': [(6, 0, self.env.ref('account.account_tag_investing').ids)],
                'company_id': cid,
            })

        if not company.default_cash_difference_income_account_id:
            company.default_cash_difference_income_account_id = self.env['account.account'].create({
                'name': _('Cash Difference Gain'),
                'code': self.env['account.account']._search_new_account_code(company, code_digits, '999'),
                'user_type_id': self.env.ref('account.data_account_type_revenue').id,
                'tag_ids': [(6, 0, self.env.ref('account.account_tag_investing').ids)],
                'company_id': cid,
            })

        # Set the transfer account on the company
        transfer_account_code_prefix = template_data['transfer_account_code_prefix']
        company.transfer_account_id = self.env['account.account'].search([
            ('code', '=like', transfer_account_code_prefix + '%'), ('company_id', '=', cid)], limit=1)

        # Create the current year earning account if it wasn't present in the CoA
        company.get_unaffected_earnings_account()

        if not company.account_sale_tax_id:
            company.account_sale_tax_id = self.env['account.tax'].search([
                ('type_tax_use', 'in', ('sale', 'all')),
                ('company_id', '=', cid)
            ], limit=1).id
        if not company.account_purchase_tax_id:
            company.account_purchase_tax_id = self.env['account.tax'].search([
                ('type_tax_use', 'in', ('purchase', 'all')),
                ('company_id', '=', cid)
            ], limit=1).id

        for field, model in [
            ('property_account_receivable_id', 'res.partner'),
            ('property_account_payable_id', 'res.partner'),
            ('property_account_expense_categ_id', 'product.category'),
            ('property_account_income_categ_id', 'product.category'),
            ('property_account_expense_id', 'product.template'),
            ('property_account_income_id', 'product.template'),
            ('property_tax_payable_account_id', 'account.tax.group'),
            ('property_tax_receivable_account_id', 'account.tax.group'),
            ('property_advance_tax_payment_account_id', 'account.tax.group'),
        ]:
            value = template_data.get(field)
            if value:
                self.env['ir.property']._set_default(field, model, ref(f"account.{cid}_{value}").id, company=company)

    ###############################################################################################
    # GENERIC Template                                                                            #
    ###############################################################################################

    def _get_template_data(self, template_code, company):
        return {
            'bank_account_code_prefix': '1014',
            'cash_account_code_prefix': '1015',
            'transfer_account_code_prefix': '1017',
            'property_account_receivable_id': 'receivable',
            'property_account_payable_id': 'payable',
            'property_account_expense_categ_id': 'expense',
            'property_account_income_categ_id': 'income',
            'property_account_expense_id': 'expense',
            'property_account_income_id': 'income',
            'property_tax_payable_account_id': 'tax_payable',
            'property_tax_receivable_account_id': 'tax_receivable',
            'property_advance_tax_payment_account_id': 'cash_diff_income',  # TODO
        }

    def _get_account_journal(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f"{cid}_sale": {
                'name': _('Customer Invoices'),
                'type': 'sale',
                'code': _('INV'),
                'default_account_id': f"account.{cid}_income",
                'show_on_dashboard': True,
                'color': 11,
                'sequence': 5,
            },
            f"{cid}_purchase": {
                'name': _('Vendor Bills'),
                'type': 'purchase',
                'code': _('BILL'),
                'default_account_id': f"account.{cid}_expense",
                'show_on_dashboard': True,
                'color': 11,
                'sequence': 6,
            },
            f"{cid}_general": {
                'name': _('Miscellaneous Operations'),
                'type': 'general',
                'code': _('MISC'),
                'show_on_dashboard': True,
                'sequence': 7,
            },
            f"{cid}_exch": {
                'name': _('Exchange Difference'),
                'type': 'general',
                'code': _('EXCH'),
                'show_on_dashboard': False,
                'sequence': 9,
            },
            f"{cid}_caba": {
                'name': _('Cash Basis Taxes'),
                'type': 'general',
                'code': _('CABA'),
                'show_on_dashboard': False,
                'sequence': 10,
            },
            f"{cid}_cash": {
                'name': _('Cash'),
                'type': 'cash',
                'suspense_account_id': f"account.{cid}_cash_diff_income",  # TODO
            },
            f"{cid}_bank": {
                'name': _('Bank'),
                'type': 'bank',
                'suspense_account_id': f"account.{cid}_cash_diff_income",  # TODO
            },
        }

    def _get_account_tax(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f"{cid}_sale_tax_template": {
                "name": _("Tax 15%"),
                "amount": 15,
                "type_tax_use": 'sale',
                "tax_group_id": f'account.{cid}_tax_group_15',
                "invoice_repartition_line_ids": [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_tax_received',
                    }),
                ],
                "refund_repartition_line_ids": [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_tax_received',
                    }),
                ],
            },
            f"{cid}_purchase_tax_template": {
                "name": _("Purchase Tax 15%"),
                "amount": 15,
                "type_tax_use": 'purchase',
                "tax_group_id": f'account.{cid}_tax_group_15',
                "invoice_repartition_line_ids": [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_tax_received',
                    }),
                ],
                "refund_repartition_line_ids": [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_tax_received',
                    }),
                ],
            },
        }

    def _get_res_company(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            self.env.company.get_metadata()[0]['xmlid']: {
                'currency_id': 'base.USD',
                'account_fiscal_country_id': 'base.us',
                'default_cash_difference_income_account_id': f'account.{cid}_cash_diff_income',
                'default_cash_difference_expense_account_id': f'account.{cid}_cash_diff_expense',
                'account_cash_basis_base_account_id': f'account.{cid}_cash_diff_income',  # TODO
                'account_default_pos_receivable_account_id': f'account.{cid}_cash_diff_income',  # TODO
                'income_currency_exchange_account_id': f'account.{cid}_income_currency_exchange',
                'expense_currency_exchange_account_id': f'account.{cid}_expense_currency_exchange',
            }
        }
