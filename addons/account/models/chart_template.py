# -*- coding: utf-8 -*-

import ast
import csv
import logging
from collections import defaultdict

from odoo import SUPERUSER_ID, Command, _, api, models
from odoo.addons.base.models.ir_translation import IrTranslationImport
from odoo.modules import get_resource_path
from odoo.http import request

_logger = logging.getLogger(__name__)

TEMPLATES = {
    'generic_coa': {'name': 'Generic Chart Template', 'country': None, 'modules': ['account']},
    'be': {'name': 'BE Belgian PCMN', 'country': 'base.be', 'modules': ['l10n_be']},
    'it': {'name': 'IT', 'country': 'base.it', 'modules': ['l10n_it']},
    'fr': {'name': 'FR', 'country': 'base.fr', 'modules': ['l10n_fr']},
    'ch': {'name': 'CH', 'country': 'base.ch', 'modules': ['l10n_ch']},
    'de': {'name': 'DE', 'country': 'base.de', 'modules': ['l10n_de']},
    'ae': {'name': 'AE', 'country': 'base.ae', 'modules': ['l10n_ae']},
}

class AccountChartTemplateDataError(Exception):
    pass


def migrate_set_tags_and_taxes_updatable(cr, registry, module):
    '''
        This is a utility function used to manually set the flag noupdate to False on tags
        and account tax templates on localization modules that need migration
        (for example in case of VAT report improvements).
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})
    xml_record_ids = env['ir.model.data'].search([
        ('model', 'in', ['account.tax.template', 'account.account.tag']),
        ('module', 'like', module)
    ]).ids
    if xml_record_ids:
        cr.execute("update ir_model_data set noupdate = 'f' where id in %s", (tuple(xml_record_ids),))

def preserve_existing_tags_on_taxes(cr, registry, module):
    '''
        This is a utility function used to preserve existing previous tags during upgrade of the module.
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})
    xml_records = env['ir.model.data'].search([('model', '=', 'account.account.tag'), ('module', 'like', module)])
    if xml_records:
        cr.execute("update ir_model_data set noupdate = 't' where id in %s", [tuple(xml_records.ids)])

class AccountChartTemplate(models.AbstractModel):
    _name = "account.chart.template"
    _description = "Account Chart Template"
    _template_code = "generic_coa"

    def _select_chart_template(self, company=False):
        company = company or self.env.company
        result = [(key, template['name']) for key, template in TEMPLATES.items()]
        if self:
            proposed = self._guess_chart_template(company)
            result.sort(key=lambda sel: (sel[0] != proposed, sel[1]))
        return result

    def _guess_chart_template(self, company=False):
        # TODO: one country can have multiple CoAs
        # TODO: also fix account/populate/res_company.py then
        company = company or self.env.company
        country = company.country_id
        default = 'generic_coa'
        if not company.country_id:
            return default
        country_code = country.get_external_id()[country.id]
        return next((key for key, template in TEMPLATES.items() if template['country'] == country_code), default)

    def try_loading(self, template_code=False, company=False, install_demo=True):
        """ Checks if the chart template can be loaded then proceeds installing it.

        :param template_code (str): code of the chart template to be loaded.
        :param company (Model<res.company>): the company we try to load the chart template on.
            If not provided, it is retrieved from the context.
        :param install_demo (bool): whether or not we should load demo data right after loading the
            chart template.
        """
        # do not use `request.env` here, it can cause deadlocks
        if not company:
            if request and hasattr(request, 'allowed_company_ids'):
                company = self.env['res.company'].browse(request.allowed_company_ids[0])
            else:
                company = self.env.company
        elif isinstance(company, int):
            company = self.env['res.company'].browse([company])

        template_code = template_code or company and self._guess_chart_template(company)

        # If we don't have any chart of account on this company, install this chart of account
        if not company.chart_template and not company.existing_accounting():
            return self._load(template_code, company, install_demo)

    def _load(self, template_code, company, install_demo):
        """ Installs this chart of accounts for the current company.
        This function is overridden in modules like point_of_sales.

        :param template_code (str): code of the chart template to be loaded.
        :param company (Model<res.company>): the company we try to load the chart template on.
            If not provided, it is retrieved from the context.
        :param install_demo (bool): whether or not we should load demo data right after loading the
            chart template.
        """
        module_names = TEMPLATES[template_code].get('modules', [])
        module_ids = self.env['ir.module.module'].search([('name', 'in', module_names), ('state', '=', 'uninstalled')])
        if module_ids:
            module_ids.sudo().button_immediate_install()
            self.env.reset()

        with_company = self.sudo().with_context(default_company_id=company.id, allowed_company_ids=[company.id])
        xml_id = company.get_metadata()[0]['xmlid']
        if not xml_id:
            with_company.env['ir.model.data']._update_xmlids([{
                'xml_id': f"base.company_{company.id}",
                'record': company
            }])

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
        company.chart_template = template_code

    def _load_data(self, data):
        def deref(values, model):
            fields = ((model._fields[k], k, v) for k, v in values.items() if k in model._fields and v)
            for field, field_idx, value in fields:
                if field.type in ('many2one', 'integer', 'many2one_reference') and isinstance(value, str):
                    values[field_idx] = self.env.ref(value).id
                elif field.type in ('one2many', 'many2many') and isinstance(value[0], (list, tuple)):
                    for first_part, *_eventual, last_part in value:
                        # (0, 0, {'test': 'account.ref_name'}) -> Command.Create({'test': 13})
                        if first_part in (Command.CREATE, Command.UPDATE):
                            deref(last_part, self.env[field.comodel_name])
                        # (6, 0, ['account.ref_name']) -> Command.Set([13])
                        if first_part == Command.SET:
                            for subvalue_idx, subvalue in enumerate(last_part):
                                if isinstance(subvalue, str):
                                    last_part[subvalue_idx] = self.env.ref(subvalue).id
            return values

        def defer(all_data):
            created_models = set()
            while all_data:
                (model, data), *all_data = all_data
                created_models.add(model)
                to_delay = defaultdict(dict)
                for xml_id, vals in data.items():
                    to_be_removed = []
                    for field_name in vals:
                        field = self.env[model]._fields.get(field_name, None)
                        if (field and
                            field.relational and
                            field.comodel_name not in created_models and
                            field.comodel_name in dict(all_data)):
                            to_be_removed.append(field_name)
                            to_delay[xml_id][field_name] = vals.get(field_name)
                    for field_name in to_be_removed:
                        del vals[field_name]
                if any(to_delay.values()):
                    all_data.append((model, to_delay))
                yield model, data

        irt_cursor = IrTranslationImport(self._cr, True)
        for model, data in defer(list(data.items())):
            _logger.debug("Loading model %s ...", model)
            translate_vals = defaultdict(list)
            create_vals = []

            for xml_id, record in data.items():
                xml_id = f"{'account.' if '.' not in xml_id else ''}{xml_id}"
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

            _logger.debug('Loading records for model %s...', model)
            created = self.env[model].sudo()._load_records(create_vals)
            _logger.debug('Loaded records for model %s', model)

            for vals, record in zip(create_vals, created):
                for translation in translate_vals[vals['xml_id']]:
                    irt_cursor.push({**translation, 'res_id': record.id})
        irt_cursor.finish()

    def _load_csv(self, template_code, company, file_name, post_sanitize=None):
        cid = (company or self.env.company).id
        Model = self.env[".".join(file_name.split(".")[:-1])]
        model_fields = Model._fields

        template = TEMPLATES.get(template_code)
        module = template['modules'][0]
        path_parts = [x for x in (module, 'data', 'template', file_name) if x]
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
                relative_path = '/'.join(path_parts)
                _logger.debug('loading %s', relative_path)
                ret = {f"{cid}_{row['id']}": sanitize_csv(row) for row in csv.DictReader(csv_file)}
                _logger.debug('loaded %s', relative_path)
                return ret
        except OSError as e:
            if path:
                _logger.info("Error reading CSV file %s: %s", path, e)
            else:
                _logger.debug("No file %s found for template '%s'", file_name, module)
            return {}

    def _setup_utility_bank_accounts(self, template_code, company, bank_prefix, code_digits):
        """
            Define basic bank accounts for the company.
            - Suspense Account
            - Outstanding Receipts/Payments Accounts
            - Cash Difference Gain/Loss Accounts
            - Liquidity Transfer Account
        """
        cid = company.id
        accounts_data = {
            'account_journal_suspense_account_id': {
                'company_id': cid,
                'name': _("Bank Suspense Account"),
                'prefix': bank_prefix,
                'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
            },
            'account_journal_payment_debit_account_id': {
                'company_id': cid,
                'name': _("Outstanding Receipts"),
                'prefix': bank_prefix,
                'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
                'reconcile': True,
            },
            'account_journal_payment_credit_account_id': {
                'company_id': cid,
                'name': _("Outstanding Payments"),
                'prefix': bank_prefix,
                'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
                'reconcile': True,
            },
            'default_cash_difference_income_account_id': {
                'company_id': cid,
                'name': _("Cash Difference Gain"),
                'prefix': '999',
                'user_type_id': self.env.ref('account.data_account_type_expenses').id,
                'tag_ids': [(6, 0, self.env.ref('account.account_tag_investing').ids)],
            },
            'default_cash_difference_expense_account_id': {
                'company_id': cid,
                'name': _("Cash Difference Loss"),
                'prefix': '999',
                'user_type_id': self.env.ref('account.data_account_type_expenses').id,
                'tag_ids': [(6, 0, self.env.ref('account.account_tag_investing').ids)],
            },
        }

        # Transfer account: if the chart_template has no parent, create the single company.transfer_account_id
        if not TEMPLATES[template_code].get('parent_id'):
            accounts_data['transfer_account_id'] = {
                'company_id': cid,
                'name': _("Liquidity Transfer"),
                'prefix': company.transfer_account_code_prefix,
                'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
                'reconcile': True,
            }

        # Create needed company's bank accounts described above
        for company_attr_name, account_data in accounts_data.items():
            if not getattr(company, company_attr_name, False):
                if not 'code' in account_data:
                    account_data['code'] = self.env['account.account']._search_new_account_code(company, code_digits, account_data.pop('prefix'))
                xml_id = account_data.pop('xml_id', None)
                account_id = self.env['account.account'].create(account_data)
                if xml_id:
                    self.env['ir.model.data']._update_xmlids([{'xml_id': xml_id, 'record': account_id}])
                setattr(company, company_attr_name, account_id)

        # Set newly created Cash difference and Suspense accounts to the Cash and Bank journals
        self.env.ref(f"account.{cid}_cash").suspense_account_id = company.account_journal_suspense_account_id
        self.env.ref(f"account.{cid}_cash").profit_account_id = company.default_cash_difference_income_account_id
        self.env.ref(f"account.{cid}_bank").suspense_account_id = company.account_journal_suspense_account_id
        self.env.ref(f"account.{cid}_bank").loss_account_id = company.default_cash_difference_expense_account_id

        # Uneffected earnings account on the company (if not present yet)
        company.get_unaffected_earnings_account()

    def _get_data(self, template_code, company, model):
        name = model.replace('.', '_')
        func = getattr(self, f"_get_{template_code}_{name}", None)
        if not func:
            func = getattr(self, f"_get_{name}", None)
        return func and func(template_code, company) or {}

    def _post_load_data(self, template_code, company):
        company = (company or self.env.company)
        cid = company.id

        template_data = self._get_data(template_code, company, 'template_data')
        additional_properties = template_data.pop('additional_properties', {})
        code_digits = int(template_data.get('code_digits', 6))
        bank_prefix = template_data.get('bank_account_code_prefix', '')

        # Apply template data to the company
        company.write({key: val for key, val in template_data.items()
                       if not key.startswith("property_") and key in company._fields})

        # Set the currency to the fiscal country's currency if not set yet, and make sure it's active
        company.currency_id = company.account_fiscal_country_id.currency_id
        company.currency_id.active = True

        # Create utility bank_accounts
        self._setup_utility_bank_accounts(template_code, company, bank_prefix, code_digits)

        # Set newly created journals as defaults for the company
        if not company.tax_cash_basis_journal_id:
            company.tax_cash_basis_journal_id = self.env.ref(f'account.{cid}_caba')
        if not company.currency_exchange_journal_id:
            company.currency_exchange_journal_id = self.env.ref(f'account.{cid}_exch')

        # Setup default Income/Expense Accounts on Sale/Purchase journals
        self.env.ref(f"account.{cid}_sale").default_account_id = self.env.ref(template_data.get('property_account_income_categ_id'))
        self.env.ref(f"account.{cid}_purchase").default_account_id = self.env.ref(template_data.get('property_account_expense_categ_id'))

        # Set default Purchase and Sale taxes on the company
        if not company.account_sale_tax_id:
            company.account_sale_tax_id = self.env['account.tax'].search([
                ('type_tax_use', 'in', ('sale', 'all')), ('company_id', '=', cid)], limit=1).id
        if not company.account_purchase_tax_id:
            company.account_purchase_tax_id = self.env['account.tax'].search([
                ('type_tax_use', 'in', ('purchase', 'all')), ('company_id', '=', cid)], limit=1).id

        for field, model in {
            **additional_properties,
            'property_account_receivable_id': 'res.partner',
            'property_account_payable_id': 'res.partner',
            'property_account_expense_categ_id': 'product.category',
            'property_account_income_categ_id': 'product.category',
            'property_account_expense_id': 'product.template',
            'property_account_income_id': 'product.template',
            'property_tax_payable_account_id': 'account.tax.group',
            'property_tax_receivable_account_id': 'account.tax.group',
            'property_advance_tax_payment_account_id': 'account.tax.group',
        }.items():
            value = template_data.get(field)
            if value:
                self.env['ir.property']._set_default(field, model, self.env.ref(value).id, company=company)

    def _get_template_data(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            'bank_account_code_prefix': '1014',
            'cash_account_code_prefix': '1015',
            'transfer_account_code_prefix': '1017',
            'property_account_receivable_id': f'account.{cid}_receivable',
            'property_account_payable_id': f'account.{cid}_payable',
            'property_account_expense_categ_id': f'account.{cid}_expense',
            'property_account_income_categ_id': f'account.{cid}_income',
            'property_account_expense_id': f'account.{cid}_expense',
            'property_account_income_id': f'account.{cid}_income',
            'property_tax_payable_account_id': f'account.{cid}_tax_payable',
            'property_tax_receivable_account_id': f'account.{cid}_tax_receivable',
            # Only LU -- 'property_advance_tax_payment_account_id': '',
        }

    # --------------------------------------------------------------------------------

    def _get_chart_template_data(self, template_code, company):
        company = company or self.env.company
        data = {}
        models = ('res.company', 'account.account', 'account.tax', 'account.tax.group', 'account.journal', 'account.group')
        try:
            for model in models:
                data[model] = self._get_data(template_code, company, model)
        except Exception as e:
            message = f"Error in data from model {model} for template '{template_code}' and company '{company.name}' ({company.id})"
            raise AccountChartTemplateDataError(message) from e
        return data

    def _get_account_account(self, template_code, company):
        return self._load_csv(template_code, company, 'account.account.csv')

    def _get_account_group(self, template_code, company):
        def account_group_sanitize(row):
            start, end = row['code_prefix_start'], row['code_prefix_end']
            if not end or end < start:
                row['code_prefix_end'] = start
            return row
        return self._load_csv(template_code, company, 'account.group.csv', post_sanitize=account_group_sanitize)

    def _get_account_journal(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            f"{cid}_sale": {
                'name': _('Customer Invoices'),
                'type': 'sale',
                'code': _('INV'),
                'show_on_dashboard': True,
                'color': 11,
                'sequence': 5,
            },
            f"{cid}_purchase": {
                'name': _('Vendor Bills'),
                'type': 'purchase',
                'code': _('BILL'),
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
            f"{cid}_bank": {
                'name': _('Bank'),
                'type': 'bank',
                'show_on_dashboard': True,
                'sequence': 11
            },
            f"{cid}_cash": {
                'name': _('Cash'),
                'type': 'cash',
                'show_on_dashboard': True,
                'sequence': 12
            },
        }

    def _get_res_company(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            company.get_external_id()[cid]: {
                'account_fiscal_country_id': 'base.us',
                'account_default_pos_receivable_account_id': f'account.{cid}_pos_receivable',
                'income_currency_exchange_account_id': f'account.{cid}_income_currency_exchange',
                'expense_currency_exchange_account_id': f'account.{cid}_expense_currency_exchange',
                # only MX ?? -- 'account_cash_basis_base_account_id': f'',
            }
        }

    def _get_account_tax_group(self, template_code, company):
        return self._load_csv(template_code, company, 'account.tax.group.csv')

    def _get_account_tax(self, template_code, company):
        cid = (company or self.env.company).id
        tax_repartition_lines = [
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
        ]
        return {
            f"{cid}_{kind}_tax_template": {
                "name": name,
                "amount": 15,
                "type_tax_use": kind,
                "tax_group_id": f'account.{cid}_tax_group_15',
                "invoice_repartition_line_ids": tax_repartition_lines,
                "refund_repartition_line_ids": tax_repartition_lines,
            } for kind, name in (
                ('sale', _('Tax 15%')),
                ('purchase', _('Purchase Tax 15%'))
            )
        }
