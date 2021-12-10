from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        res = super()._load(sale_tax_rate, purchase_tax_rate, company)
        company.account_sale_tax_id = self.env.ref(f"l10n_tr.{company.id}_tr_kdv_sale_18")
        company.account_purchase_tax_id = self.env.ref(f"l10n_tr.{company.id}_tr_kdv_purchase_18")
        return res
