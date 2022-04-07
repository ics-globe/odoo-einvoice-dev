from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html_escape
from odoo.tools.misc import formatLang, format_date, get_lang


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    display_type = fields.Selection(
        selection=[
            ('product', 'Product'),
            ('tax', 'Tax'),
            ('payment_term', 'Payment Term'),
            ('line_section', 'Section'),
            ('line_note', 'Note'),
            ('rounding', "Rounding"),
        ],
    )
    exclude_from_invoice_tab = fields.Boolean(
        compute='_compute_exclude_from_invoice_tab',
        help="Technical field used to exclude some lines from the invoice_line_ids "
             "tab in the form view.",
        store=True,  # TODO do not store
    )
    sequence = fields.Integer(default=10)
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
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
        compute='_compute_totals', store=True, readonly=False, precompute=True,
        currency_field='currency_id',
    )
    price_total = fields.Monetary(
        string='Total',
        compute='_compute_totals', store=True, readonly=False, precompute=True,
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

    @api.depends('display_type')
    def _compute_exclude_from_invoice_tab(self):
        for line in self:
            line.exclude_from_invoice_tab = line.display_type in ('tax', 'payment_term')

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for line in self:
            line.product_uom_id = line.product_id.uom_id

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                line.amount_currency = line.amount_currency or (line.debit - line.credit)  # todo _compute_amount_currency_notused
                continue
            if line.exclude_from_invoice_tab:
                continue

            line.update(line._get_price_total_and_subtotal())

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

        return product_price_unit


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

    def _get_fields_onchange_subtotal(self, price_subtotal=None, move_type=None, currency=None, company=None, date=None):
        self.ensure_one()
        return self._get_fields_onchange_subtotal_model(
            price_subtotal=price_subtotal or self.price_subtotal,
            move_type=move_type or self.move_id.move_type,
            currency=currency or self.currency_id,
            company=company or self.move_id.company_id,
            date=date or self.move_id.date,
        )

    def _get_fields_onchange_subtotal_model(self, price_subtotal, move_type, currency, company, date):
        ''' This method is used to recompute the values of 'amount_currency', 'debit', 'credit' due to a change made
        in some business fields (affecting the 'price_subtotal' field).

        :param price_subtotal:  The untaxed amount.
        :param move_type:       The type of the move.
        :param currency:        The line's currency.
        :param company:         The move's company.
        :param date:            The move's date.
        :return:                A dictionary containing 'debit', 'credit', 'amount_currency'.
        '''
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1

        amount_currency = price_subtotal * sign
        balance = currency._convert(amount_currency, company.currency_id, company, date or fields.Date.context_today(self))
        return {
            # 'amount_currency': amount_currency,
            'currency_id': currency.id,
            'balance': balance,
        }

    def _get_price_total_and_subtotal(self, price_unit=None, quantity=None, discount=None, currency=None, product=None, partner=None, taxes=None, move_type=None):
        self.ensure_one()
        return self._get_price_total_and_subtotal_model(
            price_unit=price_unit or self.price_unit,
            quantity=quantity or self.quantity,
            discount=discount or self.discount,
            currency=currency or self.currency_id,
            product=product or self.product_id,
            partner=partner or self.partner_id,
            taxes=taxes or self.tax_ids,
            move_type=move_type or self.move_id.move_type,
        )

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}

        # Compute 'price_subtotal'.
        line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * line_discount_price_unit

        # Compute 'price_total'.
        if taxes:
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(line_discount_price_unit,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res

    def _set_price_and_tax_after_fpos(self):
        self.ensure_one()
        return
        # Manage the fiscal position after that and adapt the price_unit.
        # E.g. mapping a price-included-tax to a price-excluded-tax must
        # remove the tax amount from the price_unit.
        # However, mapping a price-included tax to another price-included tax must preserve the balance but
        # adapt the price_unit to the new tax.
        # E.g. mapping a 10% price-included tax to a 20% price-included tax for a price_unit of 110 should preserve
        # 100 as balance but set 120 as price_unit.
        if self.tax_ids and self.move_id.fiscal_position_id and self.move_id.fiscal_position_id.tax_ids:
            price_subtotal = self._get_price_total_and_subtotal()['price_subtotal']
            self.tax_ids = self.move_id.fiscal_position_id.map_tax(self.tax_ids._origin)
            accounting_vals = self._get_fields_onchange_subtotal(
                price_subtotal=price_subtotal,
                currency=self.move_id.company_currency_id)
            amount_currency = accounting_vals['amount_currency']
            business_vals = self._get_fields_onchange_balance(amount_currency=amount_currency)
            if 'price_unit' in business_vals:
                self.price_unit = business_vals['price_unit']

    def _get_fields_onchange_balance(self, quantity=None, discount=None, amount_currency=None, move_type=None, currency=None, taxes=None, price_subtotal=None, force_computation=False):
        self.ensure_one()
        return self._get_fields_onchange_balance_model(
            quantity=quantity or self.quantity,
            discount=discount or self.discount,
            amount_currency=amount_currency or self.amount_currency,
            move_type=move_type or self.move_id.move_type,
            currency=currency or self.currency_id or self.move_id.currency_id,
            taxes=taxes or self.tax_ids,
            price_subtotal=price_subtotal or self.price_subtotal,
            force_computation=force_computation,
        )

    @api.model
    def _get_fields_onchange_balance_model(self, quantity, discount, amount_currency, move_type, currency, taxes, price_subtotal, force_computation=False):
        ''' This method is used to recompute the values of 'quantity', 'discount', 'price_unit' due to a change made
        in some accounting fields such as 'balance'.

        This method is a bit complex as we need to handle some special cases.
        For example, setting a positive balance with a 100% discount.

        :param quantity:        The current quantity.
        :param discount:        The current discount.
        :param amount_currency: The new balance in line's currency.
        :param move_type:       The type of the move.
        :param currency:        The currency.
        :param taxes:           The applied taxes.
        :param price_subtotal:  The price_subtotal.
        :return:                A dictionary containing 'quantity', 'discount', 'price_unit'.
        '''
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1
        amount_currency *= sign

        # Avoid rounding issue when dealing with price included taxes. For example, when the price_unit is 2300.0 and
        # a 5.5% price included tax is applied on it, a balance of 2300.0 / 1.055 = 2180.094 ~ 2180.09 is computed.
        # However, when triggering the inverse, 2180.09 + (2180.09 * 0.055) = 2180.09 + 119.90 = 2299.99 is computed.
        # To avoid that, set the price_subtotal at the balance if the difference between them looks like a rounding
        # issue.
        if not force_computation and currency.is_zero(amount_currency - price_subtotal):
            return {}

        taxes = taxes.flatten_taxes_hierarchy()
        if taxes and any(tax.price_include for tax in taxes):
            # Inverse taxes. E.g:
            #
            # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
            # -----------------------------------------------------------------------------------
            # 110           | 10% incl, 5%  |                   | 100               | 115
            # 10            |               | 10% incl          | 10                | 10
            # 5             |               | 5%                | 5                 | 5
            #
            # When setting the balance to -200, the expected result is:
            #
            # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
            # -----------------------------------------------------------------------------------
            # 220           | 10% incl, 5%  |                   | 200               | 230
            # 20            |               | 10% incl          | 20                | 20
            # 10            |               | 5%                | 10                | 10
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(amount_currency, currency=currency, handle_price_include=False)
            for tax_res in taxes_res['taxes']:
                tax = self.env['account.tax'].browse(tax_res['id'])
                if tax.price_include:
                    amount_currency += tax_res['amount']

        discount_factor = 1 - (discount / 100.0)
        if amount_currency and discount_factor:
            # discount != 100%
            vals = {
                'quantity': quantity or 1.0,
                'price_unit': amount_currency / discount_factor / (quantity or 1.0),
            }
        elif amount_currency and not discount_factor:
            # discount == 100%
            vals = {
                'quantity': quantity or 1.0,
                'discount': 0.0,
                'price_unit': amount_currency / (quantity or 1.0),
            }
        elif not discount_factor:
            # balance of line is 0, but discount  == 100% so we display the normal unit_price
            vals = {}
        else:
            # balance is 0, so unit price is 0 as well
            vals = {'price_unit': 0.0}
        return vals

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
                # values['amount_currency'] = 0
                values['debit'] = 0
                values['credit'] = 0
                values['account_id'] = False
            if self._context.get('include_business_fields'):
                line._copy_data_extend_business_fields(values)
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
        print(self, results)
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