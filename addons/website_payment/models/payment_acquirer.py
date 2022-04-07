# coding: utf-8

from odoo import fields, models
from odoo.http import request


class PaymentAcquirer(models.Model):
    _inherit = "payment.acquirer"

    website_id = fields.Many2one(
        "website",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        ondelete="restrict",
    )

    def get_base_url(self):
        # Give priority to url_root to handle multi-website cases
        # TODO VCR: REVERT THIS CHANGE
        return super().get_base_url()
