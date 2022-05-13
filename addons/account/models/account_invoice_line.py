from collections import defaultdict
from contextlib import contextmanager
from locale import currency
from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html_escape, frozendict
from odoo.tools.misc import formatLang, format_date, get_lang


class AccountInvoiceLine(models.AbstractModel):
    _name = "account.invoice.line"

    currency_id = fields.Many2one('res.currency')  # compatibility for field definition

    display_type = fields.Selection(
        selection=[
            ('product', 'Product'),
            ('tax', 'Tax'),
            ('payment_term', 'Payment Term'),
            ('line_section', 'Section'),
            ('line_note', 'Note'),
            ('rounding', "Rounding"),
        ],
        default='product',
    )
    sequence = fields.Integer(compute='_compute_sequence', store=True, readonly=False, precompute=True)
    exclude_from_invoice_tab = fields.Boolean(
        compute='_compute_exclude_from_invoice_tab',
        help="Technical field used to exclude some lines from the line_ids "
             "tab in the form view.",
        store=True,  # TODO do not store
    )
    quantity = fields.Float(
        string='Quantity',
        compute='_compute_quantity', store=True, readonly=False, precompute=True,
        digits='Product Unit of Measure',
        help="The optional quantity expressed by this line, eg: number of product sold. "
             "The quantity is not a legal requirement but is very useful for some reports.",
    )
    product_uom_id = fields.Many2one(
        string='Unit of Measure',
        comodel_name='uom.uom',
        compute='_compute_product_uom_id', store=True, readonly=False, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]",
        ondelete="restrict",
    )
    product_id = fields.Many2one(
        string='Product',
        comodel_name='product.product',
        inverse='_inverse_product_id',
        ondelete='restrict',
    )
    product_uom_category_id = fields.Many2one(
        comodel_name='uom.category',
        related='product_id.uom_id.category_id',
    )
    price_unit = fields.Float(
        string='Unit Price',
        digits='Product Price',
        compute="_compute_price_unit", store=True, readonly=False, precompute=True,
    )
    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0,
    )
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_totals',
        currency_field='currency_id',
    )
    price_total = fields.Monetary(
        string='Total',
        compute='_compute_totals',
        currency_field='currency_id',
    )
    date_maturity = fields.Date(
        string='Due Date',
        index=True,
        tracking=True,
        help="This field is used for payable and receivable journal entries. "
             "You can put the limit date for the payment of this line.",
    )
    tax_ids = fields.Many2many(
        string="Taxes",
        comodel_name='account.tax',
        compute='_compute_tax_ids', store=True, readonly=False, precompute=True,
        context={'active_test': False},
        check_company=True,
        help="Taxes that apply on the base amount",
    )
    tax_key = fields.Binary(compute='_compute_tax_key')
    compute_all_tax = fields.Binary(compute='_compute_all_tax')

    term_key = fields.Binary(compute='_compute_term_key')

    # ==== Analytic fields ====
    analytic_line_ids = fields.One2many(
        'account.analytic.line',
        'move_id',
        string='Analytic lines',
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        index='btree_not_null',
        compute="_compute_analytic_account_id", store=True, readonly=False,
        check_company=True,
        copy=True,
    )
    analytic_tag_ids = fields.Many2many(
        'account.analytic.tag',
        string='Analytic Tags',
        compute="_compute_analytic_tag_ids", store=True, readonly=False,
        check_company=True,
        copy=True,
    )

    # === Misc Information === #
    blocked = fields.Boolean(
        string='No Follow-up',
        default=False,
        help="You can check this box to mark this journal item as a litigation with the "
             "associated partner",
    )

    def _inverse_product_id(self):
        for line in self:
            fiscal_position = line.move_id.fiscal_position_id
            accounts = line.with_company(line.company_id).product_id\
                .product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
            if line.move_id.is_sale_document(include_receipts=True):
                # Out invoice.
                line.account_id = accounts['income'] or line.account_id
            elif line.move_id.is_purchase_document(include_receipts=True):
                # In invoice.
                line.account_id = accounts['expense'] or line.account_id

    @api.depends('display_type', 'partner_id')
    def _compute_account_id(self):
        term_lines = self.filtered(lambda line: line.display_type == 'payment_term')
        if term_lines:
            moves = term_lines.move_id
            self.env.cr.execute(f"""
                WITH previous AS (
                    SELECT DISTINCT ON (line.move_id)
                           'account.move' AS model,
                           line.move_id AS id,
                           NULL AS type,
                           line.account_id AS account_id
                      FROM account_move_line line
                     WHERE line.move_id = ANY(%(move_ids)s)
                       AND line.display_type = 'payment_term'
                       AND line.id != ANY(%(current_ids)s)
                ),
                properties AS(
                    SELECT DISTINCT ON (property.company_id, property.name)
                           'res.partner' AS model,
                           COALESCE(
                               SUBSTR(property.res_id, {len('res.partner') + 2})::integer,
                               company.partner_id
                           ) AS id,
                           CASE
                               WHEN property.name = 'property_account_receivable_id' THEN 'receivable'
                               ELSE 'payable'
                           END AS type,
                           SUBSTR(property.value_reference, {len('account.account') + 2})::integer AS account_id
                      FROM ir_property property
                      JOIN res_company company ON property.company_id = company.id
                     WHERE property.name IN ('property_account_receivable_id', 'property_account_payable_id')
                       AND property.company_id = ANY(%(company_ids)s)
                       AND (property.res_id = ANY(%(partners)s) OR property.res_id IS NULL)
                  ORDER BY property.company_id, property.name, property.res_id NULLS LAST
                ),
                fallback AS (
                    SELECT DISTINCT ON (account.company_id, account.internal_type)
                           'res.company' AS model,
                           account.company_id AS id,
                           account.internal_type AS type,
                           account.id AS account_id
                      FROM account_account account
                     WHERE account.company_id = ANY(%(company_ids)s)
                       AND account.internal_type IN ('receivable', 'payable')
                )
                SELECT * FROM previous
                UNION ALL
                SELECT * FROM properties
                UNION ALL
                SELECT * FROM fallback
            """, {
                'company_ids': moves.company_id.ids,
                'move_ids': moves.ids,
                'partners': [f'res.partner,{pid}' for pid in moves.commercial_partner_id.ids],
                'current_ids': term_lines.ids
            })
            accounts = {
                (model, id, internal_type): account_id
                for model, id, internal_type, account_id in self.env.cr.fetchall()
            }
            for line in term_lines:
                internal_type = 'receivable' if line.move_id.is_sale_document() else 'payable'
                move = line.move_id
                line.account_id = (
                    accounts.get(('account.move', move.id, None))
                    or accounts.get(('res.partner', move.commercial_partner_id.id, internal_type))
                    or accounts.get(('res.partner', move.company_id.partner_id.id, internal_type))
                    or accounts.get(('res.company', move.company_id.id, internal_type))
                )
        super()._compute_account_id()


    @api.depends('display_type')
    def _compute_exclude_from_invoice_tab(self):
        for line in self:
            line.exclude_from_invoice_tab = line.display_type in ('tax', 'payment_term', 'rounding')

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for line in self:
            line.product_uom_id = line.product_id.uom_id

    @api.depends('display_type')
    def _compute_quantity(self):
        for line in self:
            line.quantity = 1 if line.display_type == 'product' else False

    @api.depends('display_type')
    def _compute_sequence(self):
        seq_map = {
            'tax': 8000,
            'rounding': 9999,
            'payment_term': 10000,
        }
        for line in self:
            line.sequence = seq_map.get(line.display_type, 100)

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        for line in self:
            if line.exclude_from_invoice_tab:
                line.price_total = line.price_subtotal = False
            # Compute 'price_subtotal'.
            line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line_discount_price_unit

            # Compute 'price_total'.
            if line.tax_ids:
                force_sign = -1 if line.move_id.move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
                taxes_res = line.tax_ids.with_context(force_sign=force_sign).compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.move_id.move_type in ('out_refund', 'in_refund'),
                )
                line.price_subtotal = taxes_res['total_excluded']
                line.price_total = taxes_res['total_included']
            else:
                line.price_total = line.price_subtotal = subtotal

    @api.depends('product_id', 'product_uom_id')
    def _compute_price_unit(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue
            line.price_unit = line._get_computed_price_unit()

    def _get_computed_price_unit(self):
        ''' Helper to get the default price unit based on the product by taking care of the taxes
        set on the product and the fiscal position.
        :return: The price unit.
        '''
        self.ensure_one()

        if not self.product_id:
            return 0.0

        company = self.move_id.company_id
        currency = self.move_id.currency_id
        company_currency = company.currency_id
        product_uom = self.product_id.uom_id
        fiscal_position = self.move_id.fiscal_position_id
        is_refund_document = self.move_id.move_type in ('out_refund', 'in_refund')
        move_date = self.move_id.date or fields.Date.context_today(self)

        if self.move_id.is_sale_document(include_receipts=True):
            product_price_unit = self.product_id.lst_price
            product_taxes = self.product_id.taxes_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            product_price_unit = self.product_id.standard_price
            product_taxes = self.product_id.supplier_taxes_id
        else:
            return 0.0
        product_taxes = product_taxes.filtered(lambda tax: tax.company_id == company)

        # Apply unit of measure.
        if self.product_uom_id and self.product_uom_id != product_uom:
            product_price_unit = product_uom._compute_price(product_price_unit, self.product_uom_id)

        # Apply fiscal position.
        if product_taxes and fiscal_position:
            product_taxes_after_fp = fiscal_position.map_tax(product_taxes)

            if set(product_taxes.ids) != set(product_taxes_after_fp.ids):
                flattened_taxes_before_fp = product_taxes._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes_before_fp):
                    taxes_res = flattened_taxes_before_fp.compute_all(
                        product_price_unit,
                        quantity=1.0,
                        currency=company_currency,
                        product=self.product_id,
                        partner=self.partner_id,
                        is_refund=is_refund_document,
                    )
                    product_price_unit = company_currency.round(taxes_res['total_excluded'])

                flattened_taxes_after_fp = product_taxes_after_fp._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes_after_fp):
                    taxes_res = flattened_taxes_after_fp.compute_all(
                        product_price_unit,
                        quantity=1.0,
                        currency=company_currency,
                        product=self.product_id,
                        partner=self.partner_id,
                        is_refund=is_refund_document,
                        handle_price_include=False,
                    )
                    for tax_res in taxes_res['taxes']:
                        tax = self.env['account.tax'].browse(tax_res['id'])
                        if tax.price_include:
                            product_price_unit += tax_res['amount']

        # Apply currency rate.
        # if currency and currency != company_currency:
        #     product_price_unit = company_currency._convert(product_price_unit, currency, company, move_date)

        return product_price_unit# * self.currency_rate

    @api.depends('product_id', 'product_uom_id')
    def _compute_tax_ids(self):
        for line in self:
            if line.display_type in ('line_section', 'line_note'):
                continue
            # /!\ Don't remove existing taxes if there is no explicit taxes set on the account.
            if line.product_id or line.account_id.tax_ids or not line.tax_ids:
                taxes = line._get_computed_taxes()
                if taxes and line.move_id.fiscal_position_id:
                    taxes = line.move_id.fiscal_position_id.map_tax(taxes)
                line.tax_ids = taxes

    def _get_computed_taxes(self):
        self.ensure_one()

        if self.move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            if self.product_id.taxes_id:
                tax_ids = self.product_id.taxes_id.filtered(lambda tax: tax.company_id == self.move_id.company_id)
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids
            else:
                tax_ids = self.env['account.tax']
            if not tax_ids and not self.exclude_from_invoice_tab:
                tax_ids = self.move_id.company_id.account_sale_tax_id
        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            if self.product_id.supplier_taxes_id:
                tax_ids = self.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == self.move_id.company_id)
            elif self.account_id.tax_ids:
                tax_ids = self.account_id.tax_ids
            else:
                tax_ids = self.env['account.tax']
            if not tax_ids and not self.exclude_from_invoice_tab:
                tax_ids = self.move_id.company_id.account_purchase_tax_id
        else:
            # Miscellaneous operation.
            tax_ids = self.account_id.tax_ids

        if self.company_id and tax_ids:
            tax_ids = tax_ids.filtered(lambda tax: tax.company_id == self.company_id)

        return tax_ids

    @api.depends('tax_ids', 'currency_id', 'partner_id', 'account_id', 'group_tax_id', 'analytic_tag_ids', 'analytic_account_id')
    def _compute_tax_key(self):
        for line in self:
            if line.tax_repartition_line_id:
                line.tax_key = frozendict({
                    'tax_repartition_line_id': line.tax_repartition_line_id.id,
                    'group_tax_id': line.group_tax_id.id,
                    'account_id': line.account_id.id,
                    'currency_id': line.currency_id.id,
                    'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids or [])],
                    'analytic_account_id': line.analytic_account_id.id,
                    'tax_ids': [(6, 0, line.tax_ids.ids)],
                    'tax_tag_ids': [(6, 0, line.tax_tag_ids.ids)],
                    'partner_id': line.partner_id.id,
                    'move_id': line.move_id.id,
                })
            else:
                line.tax_key = frozendict({'id': line.id})

    @api.depends('tax_ids', 'currency_id', 'partner_id', 'analytic_tag_ids', 'analytic_account_id', 'balance', 'partner_id', 'move_id.partner_id')
    def _compute_all_tax(self):
        for line in self:
            sign = -1 if line.move_id.is_inbound() else 1
            compute_all_currency = line.tax_ids.with_context(force_sign=sign).compute_all(
                sign * line.price_unit * (1 - line.discount / 100) or line.amount_currency,
                currency=line.currency_id,
                quantity=line.quantity,
                product=line.product_id,
                partner=line.move_id.partner_id or line.partner_id,
                is_refund=line.move_id.move_type in ('in_refund', 'out_refund'),
                handle_price_include=line.move_id.is_invoice(),
                include_caba_tags=line.move_id.always_tax_exigible,
            )
            compute_all = line.tax_ids.with_context(force_sign=sign).compute_all(
                sign * line.price_unit / line.currency_rate * (1 - line.discount / 100) or line.balance,
                currency=line.currency_id,
                quantity=line.quantity,
                product=line.product_id,
                partner=line.move_id.partner_id or line.partner_id,
                is_refund=line.move_id.move_type in ('in_refund', 'out_refund'),
                handle_price_include=line.move_id.is_invoice(),
                include_caba_tags=line.move_id.always_tax_exigible,
            )
            line.compute_all_tax = {
                frozendict({
                    'tax_repartition_line_id': tax['tax_repartition_line_id'],
                    'group_tax_id': tax['group'] and tax['group'].id or False,
                    'account_id': tax['account_id'] or line.account_id.id,
                    'currency_id': line.currency_id.id,
                    'analytic_tag_ids': [(6, 0, tax['analytic'] and line.analytic_tag_ids.ids or [])],
                    'analytic_account_id': tax['analytic'] and line.analytic_account_id.id,
                    'tax_ids': [(6, 0, tax['tax_ids'])],
                    'tax_tag_ids': [(6, 0, tax['tag_ids'])],
                    'partner_id': (line.move_id or line).partner_id.id,
                    'move_id': line.move_id.id,
                }): {
                    'name': tax['name'],
                    'balance': tax['amount'],
                    'amount_currency': tax_currency['amount'],
                }
                for tax, tax_currency in zip(compute_all['taxes'], compute_all_currency['taxes'])
            }
            if not line.tax_repartition_line_id:
                line.compute_all_tax[frozendict({'id': line.id})] = {
                    'tax_tag_ids': self.env['account.account.tag'].browse(compute_all['base_tags']),
                }

    @api.depends('date_maturity')
    def _compute_term_key(self):
        for line in self:
            if line.display_type in 'payment_term':
                line.term_key = frozendict({
                    'move_id': line.move_id.id,
                    'date_maturity': fields.Date.to_date(line.date_maturity),
                })
            else:
                line.term_key = False

    @api.depends('product_id', 'account_id', 'partner_id', 'date')
    def _compute_analytic_account_id(self):
        for record in self:
            if not record.exclude_from_invoice_tab or not record.move_id.is_invoice(include_receipts=True):
                rec = self.env['account.analytic.default'].account_get(
                    product_id=record.product_id.id,
                    partner_id=record.partner_id.commercial_partner_id.id or record.move_id.partner_id.commercial_partner_id.id,
                    account_id=record.account_id.id,
                    user_id=record.env.uid,
                    date=record.date,
                    company_id=record.move_id.company_id.id
                )
                if rec:
                    record.analytic_account_id = rec.analytic_id

    @api.depends('product_id', 'account_id', 'partner_id', 'date')
    def _compute_analytic_tag_ids(self):
        for record in self:
            if not record.exclude_from_invoice_tab or not record.move_id.is_invoice(include_receipts=True):
                rec = self.env['account.analytic.default'].account_get(
                    product_id=record.product_id.id,
                    partner_id=record.partner_id.commercial_partner_id.id or record.move_id.partner_id.commercial_partner_id.id,
                    account_id=record.account_id.id,
                    user_id=record.env.uid,
                    date=record.date,
                    company_id=record.move_id.company_id.id
                )
                if rec:
                    record.analytic_tag_ids = rec.analytic_tag_ids

    # -------------------------------------------------------------------------
    # ANALYTIC
    # -------------------------------------------------------------------------

    def _prepare_analytic_line(self):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            an analytic account. This method is intended to be extended in other modules.
            :return list of values to create analytic.line
            :rtype list
        """
        result = []
        for move_line in self:
            amount = (move_line.credit or 0.0) - (move_line.debit or 0.0)
            default_name = move_line.name or (move_line.ref or '/' + ' -- ' + (move_line.partner_id and move_line.partner_id.name or '/'))
            category = 'other'
            if move_line.move_id.is_sale_document():
                category = 'invoice'
            elif move_line.move_id.is_purchase_document():
                category = 'vendor_bill'
            result.append({
                'name': default_name,
                'date': move_line.date,
                'account_id': move_line.analytic_account_id.id,
                'group_id': move_line.analytic_account_id.group_id.id,
                'tag_ids': [(6, 0, move_line._get_analytic_tag_ids())],
                'unit_amount': move_line.quantity,
                'product_id': move_line.product_id and move_line.product_id.id or False,
                'product_uom_id': move_line.product_uom_id and move_line.product_uom_id.id or False,
                'amount': amount,
                'general_account_id': move_line.account_id.id,
                'ref': move_line.ref,
                'move_id': move_line.id,
                'user_id': move_line.move_id.invoice_user_id.id or self._uid,
                'partner_id': move_line.partner_id.id,
                'company_id': move_line.analytic_account_id.company_id.id or move_line.move_id.company_id.id,
                'category': category,
            })
        return result

    def _prepare_analytic_distribution_line(self, distribution):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            analytic tags with analytic distribution.
        """
        self.ensure_one()
        amount = -self.balance * distribution.percentage / 100.0
        default_name = self.name or (self.ref or '/' + ' -- ' + (self.partner_id and self.partner_id.name or '/'))
        return {
            'name': default_name,
            'date': self.date,
            'account_id': distribution.account_id.id,
            'group_id': distribution.account_id.group_id.id,
            'partner_id': self.partner_id.id,
            'tag_ids': [(6, 0, [distribution.tag_id.id] + self._get_analytic_tag_ids())],
            'unit_amount': self.quantity,
            'product_id': self.product_id and self.product_id.id or False,
            'product_uom_id': self.product_uom_id and self.product_uom_id.id or False,
            'amount': amount,
            'general_account_id': self.account_id.id,
            'ref': self.ref,
            'move_id': self.id,
            'user_id': self.move_id.invoice_user_id.id or self._uid,
            'company_id': distribution.account_id.company_id.id or self.env.company.id,
        }

    def _get_analytic_tag_ids(self):
        self.ensure_one()
        return self.analytic_tag_ids.filtered(lambda r: not r.active_analytic_distribution).ids

    def create_analytic_lines(self):
        """ Create analytic items upon validation of an account.move.line having an analytic account or an analytic distribution.
        """
        lines_to_create_analytic_entries = self.env['account.move.line']
        analytic_line_vals = []
        for obj_line in self:
            for tag in obj_line.analytic_tag_ids.filtered('active_analytic_distribution'):
                for distribution in tag.analytic_distribution_ids:
                    analytic_line_vals.append(obj_line._prepare_analytic_distribution_line(distribution))
            if obj_line.analytic_account_id:
                lines_to_create_analytic_entries |= obj_line

        # create analytic entries in batch
        if lines_to_create_analytic_entries:
            analytic_line_vals += lines_to_create_analytic_entries._prepare_analytic_line()

        self.env['account.analytic.line'].create(analytic_line_vals)

    # -------------------------------------------------------------------------
    # CRUD/ORM
    # -------------------------------------------------------------------------

    def _copy_data_extend_business_fields(self, values):
        # TODO remove this...
        self.ensure_one()

    def copy_data(self, default=None):
        res = super().copy_data(default=default)

        for line, values in zip(self, res):
            # Don't copy the name of a payment term line.
            if line.move_id.is_invoice() and line.account_id.user_type_id.type in ('receivable', 'payable'):
                values['name'] = ''
            # Don't copy restricted fields of notes
            if line.display_type in ('line_section', 'line_note'):
                values['debit'] = 0
                values['credit'] = 0
                values['account_id'] = False
            if self._context.get('include_business_fields'):
                line._copy_data_extend_business_fields(values)
        return res

    def _sync_invoice(self):
        if self.env.context.get('skip_sync_invoice'):
            return  # avoid infinite recursion
        for line in self.with_context(skip_sync_invoice=True).filtered(lambda l: l.move_id.is_invoice() and l.display_type == 'product'):
            sign = line.move_id.direction_sign
            balance = sign * line.company_id.currency_id.round(line.price_subtotal / line.currency_rate)
            amount_currency = sign * line.currency_id.round(line.price_subtotal)
            if line.amount_currency != amount_currency:
                line.amount_currency = amount_currency
            if line.balance != line.amount_currency / line.currency_rate:
                line.balance = balance

    @api.model_create_multi
    def create(self, vals_list):
        from pprint import pprint
        # pprint(['create', vals_list])
        moves = self.env['account.move'].browse({vals['move_id'] for vals in vals_list})
        with moves._sync_dynamic_lines():
            lines = super().create(vals_list)
            lines.with_context(check_move_validity=False)._sync_invoice()
        if self.env.context.get('check_move_validity', True):
            lines.move_id._check_balanced()
        return lines

    def write(self, vals):
        if not vals:
            return True
        from pprint import pprint
        # pprint(['write', self, vals])
        with self.move_id._sync_dynamic_lines():
            res = super().write(vals)
            self.with_context(check_move_validity=False)._sync_invoice()
        if self.env.context.get('check_move_validity', True):
            self.move_id._check_balanced()
        return res

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def reconcile(self):
        # List unpaid invoices
        not_paid_invoices = self.move_id.filtered(lambda move:
            move.is_invoice(include_receipts=True)
            and move.payment_state not in ('paid', 'in_payment')
        )
        results = super().reconcile()
        # Trigger action for paid invoices
        not_paid_invoices.filtered(lambda move:
            move.payment_state in ('paid', 'in_payment')
        ).action_invoice_paid()
        return results

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _belongs_to_refund(self):
        """ Tells whether or not this move line corresponds to a refund operation.
        """
        self.ensure_one()

        if self.tax_repartition_line_id:
            return self.tax_repartition_line_id.refund_tax_id

        elif self.move_id.move_type == 'entry':
            tax_type = self.tax_ids[0].type_tax_use if self.tax_ids else None
            return (tax_type == 'sale' and self.debit) or (tax_type == 'purchase' and self.credit)

        return self.move_id.move_type in ('in_refund', 'out_refund')


class AccountMoveLine(models.AbstractModel):
    _name = 'account.move.line'
    _inherit = ['account.invoice.line', 'account.move.line']