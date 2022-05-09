# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('transfer', "Wire Transfer")], default='transfer',
        ondelete={'transfer': 'set default'})
    qr_code = fields.Boolean(
        string="Enable QR Codes", help="Enable the use of QR-codes when paying by wire transfer.")

    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to hide the credentials page.

        :return: None
        """
        super()._compute_view_configuration_fields()
        self.filtered(lambda pro: pro.code == 'transfer').write({
            'show_credentials_page': False,
            'show_payment_icon_ids': False,
            'show_pre_msg': False,
            'show_done_msg': False,
            'show_cancel_msg': False,
        })

    @api.model_create_multi
    def create(self, values_list):
        """ Make sure to have a pending_msg set. """
        # This is done here and not in a default to have access to all required values.
        providers = super().create(values_list)
        providers._transfer_ensure_pending_msg_is_set()
        return providers

    def write(self, values):
        """ Make sure to have a pending_msg set. """
        # This is done here and not in a default to have access to all required values.
        res = super().write(values)
        self._transfer_ensure_pending_msg_is_set()
        return res

    def _transfer_ensure_pending_msg_is_set(self):
        for provider in self.filtered(lambda pro: pro.code == 'transfer' and not pro.pending_msg):
            company_id = provider.company_id.id
            # filter only bank accounts marked as visible
            accounts = self.env['account.journal'].search([
                ('type', '=', 'bank'), ('company_id', '=', company_id)
            ]).bank_account_id
            provider.pending_msg = f'<div>' \
                f'<h3>{_("Please use the following transfer details")}</h3>' \
                f'<h4>{_("Bank Account") if len(accounts) == 1 else _("Bank Accounts")}</h4>' \
                f'<ul>{"".join(f"<li>{account.display_name}</li>" for account in accounts)}</ul>' \
                f'<h4>{_("Communication")}</h4>' \
                f'<p>{_("Please use the order name as communication reference.")}</p>' \
                f'</div>'
