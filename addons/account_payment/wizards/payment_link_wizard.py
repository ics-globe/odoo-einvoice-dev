# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentLinkWizard(models.TransientModel):
    _inherit = 'payment.link.wizard'

    def _get_link_values(self):
        res = super()._get_link_values()
        if self.res_model == 'account.move':
            res['invoice_id'] = self.res_id
        return res
