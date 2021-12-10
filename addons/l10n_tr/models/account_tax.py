from odoo import fields, models

class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_tr_code = fields.Char(string="Code", size=3)
    l10n_tr_tax_type = fields.Selection(selection=[
        ('normal', 'Normal'),
        ('exception', 'Exception'),
        ('withdraw', 'VAT Withdraw'),
    ], default='normal', string="Exception",
        help="Technical field showing that this tax will be applied with "
             "TaxExemptionReasonCode tag or with WithholdingTaxTotal tag in EDI.")


class AccountTaxTemplate(models.Model):
    _inherit = "account.tax.template"

    l10n_tr_code = fields.Char(string="Code", size=3)
    l10n_tr_tax_type = fields.Selection(selection=[
        ('normal', 'Normal'),
        ('exception', 'Exception'),
        ('withdraw', 'VAT Withdraw'),
    ], default='normal', string="Exception",
        help="Technical field showing that this tax will be applied with "
             "TaxExemptionReasonCode tag or with WithholdingTaxTotal tag in EDI.")


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    l10n_tr_code = fields.Char(string="Code", size=4)
