# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        for invoice in self:
            invoice.amount_total_words = invoice.currency_id.amount_to_text(invoice.amount_total)

    amount_total_words = fields.Char('Total (In Words)', compute='_compute_amount_total_words')

    l10n_in_gst_treatment = fields.Selection([
            ('regular', 'Registered Business - Regular'),
            ('composition', 'Registered Business - Composition'),
            ('unregistered', 'Unregistered Business'),
            ('consumer', 'Consumer'),
            ('overseas', 'Overseas'),
            ('special_economic_zone', 'Special Economic Zone'),
            ('deemed_export', 'Deemed Export')
        ], string='GST Treatment', readonly=True, states={'draft': [('readonly', False)]})

    l10n_in_state_id = fields.Many2one('res.country.state', 
        string='Place of Supply',
        readonly=True, states={'draft': [('readonly', False)]})
    
    l10n_in_company_country_code = fields.Char(related='company_id.country_id.code', 
        string='Country code')

    l10n_in_gstin = fields.Char(string='GSTIN',
        readonly=True, states={'draft': [('readonly', False)]})

    # For Export invoice this data is need in GSTR report
    l10n_in_shipping_bill_number = fields.Char('Shipping bill number', 
        readonly=True, states={'draft': [('readonly', False)]})

    l10n_in_shipping_bill_date = fields.Date('Shipping bill date', 
        readonly=True, 
        states={'draft': [('readonly', False)]})

    l10n_in_shipping_port_code_id = fields.Many2one('l10n_in.port.code', 
        string='Port code', 
        states={'draft': [('readonly', False)]})

    l10n_in_reseller_partner_id = fields.Many2one('res.partner', 
        string='Reseller', 
        domain=[('vat', '!=', False)], 
        help='Only Registered Reseller', 
        readonly=True, 
        states={'draft': [('readonly', False)]})
    
    tax_amount_by_lines = fields.Binary(string='Tax amount for lines',
        compute='_compute_invoice_taxes_by_line_by_group',
        help='Tax amount by group for the invoice line.')

    def _compute_invoice_taxes_by_line_by_group(self):
        for invoice in self:
            taxes = dict()
            for line in invoice.invoice_line_ids:
                taxes[line.id] = line.tax_amount_by_tax_group
            invoice.tax_amount_by_lines = taxes

    l10n_in_shipping_partner_id = fields.Many2one(compute='compute_l10n_in_shipping_partner',
        comodel_name='res.partner',
        string='Computed Delivery Address')

    def compute_l10n_in_shipping_partner(self):
        for invoice in self:
            invoice.l10n_in_shipping_partner_id = invoice.partner_id

    l10n_in_company_partner_id = fields.Many2one(compute='compute_l10n_in_company_partner_id',
        comodel_name='res.partner',
        string='Company/GSTN Unit')

    def compute_l10n_in_company_partner_id(self):
        for invoice in self:
            invoice.l10n_in_company_partner_id = invoice.journal_id.l10n_in_gstin_partner_id or invoice.journal_id.company_id.partner_id

    l10n_in_partner_state_id = fields.Many2one(compute='compute_l10n_in_partner_state_id',
        comodel_name='res.country.state',
        string='Partner State')

    def compute_l10n_in_partner_state_id(self):
        for invoice in self:
            invoice.l10n_in_partner_state_id = False
            if invoice.journal_id.type == 'sale' and invoice.l10n_in_shipping_partner_id:
                country_code = invoice.l10n_in_shipping_partner_id.country_id.code
                state_id = invoice.l10n_in_shipping_partner_id.state_id
                if country_code == 'IN' and state_id:
                    invoice.l10n_in_partner_state_id = state_id
                elif country_code != 'IN':
                    invoice.l10n_in_partner_state_id = self.env.ref('l10n_in.state_in_ot')
            elif invoice.journal_id.type == 'purchase':
                invoice.l10n_in_partner_state_id = invoice.l10n_in_company_partner_id.state_id.id

    @api.onchange('partner_id', 'journal_id')
    def _onchange_partner_id(self):
        res = super()._onchange_partner_id()
        if self.l10n_in_company_country_code == 'IN' and self.journal_id.type in ('sale', 'purchase'):
            self.l10n_in_gst_treatment = self.partner_id.l10n_in_gst_treatment
            self.l10n_in_gstin = self.partner_id.vat
            self.l10n_in_state_id = self.l10n_in_partner_state_id.id
        return res

    @api.model
    def _get_tax_grouping_key_from_tax_line(self, tax_line):
        res = super()._get_tax_grouping_key_from_tax_line(tax_line)
        if self.l10n_in_company_country_code != 'IN':
            return res

        res.update({
            'base_line_ref': tax_line.ref,
        })
        return res

    @api.model
    def _get_tax_grouping_key_from_base_line(self, base_line, tax_vals):
        res = super()._get_tax_grouping_key_from_base_line(base_line, tax_vals)
        if self.l10n_in_company_country_code != 'IN':
            return res

        ref = base_line._origin.id or base_line.id.ref or base_line.id
        base_line.base_line_ref = ref
        res.update({
            'base_line_ref': ref,
        })
        return res

    @api.model
    def _get_tax_key_for_group_add_base(self, line):
        tax_key = super(AccountMove, self)._get_tax_key_for_group_add_base(line)
        if self.l10n_in_company_country_code != 'IN':
            return tax_key
        tax_key += [line.id,]
        return tax_key

    def _post(self, soft=True):
        gst_treatment_name_mapping = {k: v for k, v in self._fields['l10n_in_gst_treatment']._description_selection(self.env)}

        for invoice in self:
            if invoice.l10n_in_company_country_code != 'IN' or invoice.journal_id.type not in ('sale', 'purchase'):
                continue

            if not invoice.l10n_in_gstin and invoice.l10n_in_gst_treatment in ['regular', 'composition', 'special_economic_zone', 'deemed_export']:
                raise ValidationError(_(
                    "GST Number is required for %(partner_name)s (%(partner_id)s) under GST treatment %(name)s",
                    partner_name = invoice.l10n_in_shipping_partner_id.name,
                    partner_id = invoice.l10n_in_shipping_partner_id.id,
                    name = gst_treatment_name_mapping.get(invoice.l10n_in_gst_treatment)
                ))

            if invoice.l10n_in_company_partner_id and not invoice.l10n_in_company_partner_id.state_id:
                raise ValidationError(_(
                    "State is missing from Company or GSTN Unit: %(company_name)s (%(company_id)s).",
                    company_name = invoice.l10n_in_company_partner_id.name,
                    company_id = invoice.l10n_in_company_partner_id.id
                ))

            if invoice.partner_id and not invoice.l10n_in_partner_state_id:
                raise ValidationError(_("State is missing from Customer '%s'. \
                    Set the state and post this invoice again.", invoice.l10n_in_shipping_partner_id.name))
            
            if not invoice.l10n_in_state_id:
                invoice.l10n_in_state_id = invoice.l10n_in_partner_state_id.id
            
            if not invoice.l10n_in_gstin:
                invoice.l10n_in_gstin = invoice.partner_id.vat
        return super()._post(soft)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    #it would be good to use the many2one fields instead of char, but required
    #framework fix for onchnage/create, we just need the referance to search the
    #related tax lines so char field would be ok as of now.
    base_line_ref = fields.Char('Matching Ref',
        help='Technical field to map invoice base line with its tax lines.')
    
    tax_amount_by_tax_group = fields.Binary(string='Tax amount by group',
        compute='_compute_invoice_line_taxes_by_group',
        help='Tax amount by group for the line.')
    
    def _compute_invoice_line_taxes_by_group(self):
        # prepare the dict of tax values by tax group
        # line.tax_amount_by_tax_group = {'SGST': 9.0, 'CGST': 9.0, 'Cess': 2.0}
        for line in self:
            move_id = line.move_id
            taxes = dict()
            for ln in self.search([('base_line_ref','=',str(line.id)), ('tax_line_id','!=',False), ('move_id','=',line.move_id.id)]):
                tax_group_name = ln.tax_line_id.tax_group_id.name.upper()
                taxes.setdefault(tax_group_name, 0.0)
                if not self._context.get('in_company_currency') and move_id.currency_id and move_id.company_id.currency_id != move_id.currency_id:
                    taxes[tax_group_name] += ln.amount_currency * (move_id.is_inbound and -1 or 1)
                else:
                    taxes[tax_group_name] += ln.balance * (move_id.is_inbound and -1 or 1)
            line.tax_amount_by_tax_group = taxes

    def _update_base_line_ref(self):
        #search for the invoice lines on which the taxes applied
        base_lines = self.filtered(lambda ln: ln.tax_ids)
        for line in base_lines:
            #filters the tax lines related to the base lines and replace virtual_id with the database id
            tax_lines = self.filtered(lambda ln: ln.base_line_ref == line.base_line_ref and not ln.tax_ids)
            tax_lines += line
            tax_lines.write({
                'base_line_ref': line.id,
            })

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._update_base_line_ref()
        return lines
        