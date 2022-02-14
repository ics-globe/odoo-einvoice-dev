from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_tr_code = fields.Char(string="Reason Code", size=3, help="The reason code or tax sub-code applied to this tax")
    l10n_tr_tax_type = fields.Selection(related="tax_group_id.l10n_tr_tax_type")


class AccountTaxTemplate(models.Model):
    _inherit = "account.tax.template"

    l10n_tr_code = fields.Char(string="Reason Code", size=3)


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    l10n_tr_code = fields.Char(string="Code", size=4)
    l10n_tr_tax_type = fields.Selection(selection=[
                ('normal', 'Normal'),
                ('exception', 'Exception'),
                ('withdraw', 'VAT Partial Withdraw'),
            ], default='normal', string="Exception",
        help="Technical field showing that this tax will be applied with "
             "TaxExemptionReasonCode tag or with WithholdingTaxTotal tag in EDI.")
