# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, _
from odoo.exceptions import ValidationError
from odoo.http import request, route

from odoo.addons.account.controllers import portal as account_portal
from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.portal.controllers.portal import _build_url_w_params


class PortalAccount(account_portal.PortalAccount):

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = super()._invoice_get_page_view_values(invoice, access_token, **kwargs)
        logged_in = not request.env.user._is_public()
        # We set partner_id to the partner id of the current user if logged in, otherwise we set it
        # to the invoice partner id. We do this to ensure that payment tokens are assigned to the
        # correct partner and to avoid linking tokens to the public user.
        partner_id = request.env.user.partner_id.id if logged_in else invoice.partner_id.id
        acquirers_sudo = request.env['payment.acquirer'].sudo()._get_compatible_acquirers(
            invoice.company_id.id or request.env.company.id,
            partner_id,
            currency_id=invoice.currency_id.id,
        )  # In sudo mode to read the fields of acquirers and partner (if not logged in)
        tokens = request.env['payment.token'].search(
            [('acquirer_id', 'in', acquirers_sudo.ids), ('partner_id', '=', partner_id)]
        )  # Tokens are cleared at the end if the user is not logged in
        fees_by_acquirer = {
            acq_sudo: acq_sudo._compute_fees(
                invoice.amount_total, invoice.currency_id, invoice.partner_id.country_id
            ) for acq_sudo in acquirers_sudo.filtered('fees_active')
        }
        values.update({
            'acquirers': acquirers_sudo,
            'tokens': tokens,
            'fees_by_acquirer': fees_by_acquirer,
            'show_tokenize_input': logged_in,  # Prevent public partner from saving payment methods
            'amount': invoice.amount_residual,
            'currency': invoice.currency_id,
            'partner_id': partner_id,
            'access_token': access_token,
            'transaction_route': f'/invoice/transaction/{invoice.id}/',
            'landing_route': _build_url_w_params(invoice.access_url, {'access_token': access_token})
        })
        if not logged_in:
            # Don't display payment tokens of the invoice partner if the user is not logged in, but
            # inform that logging in will make them available.
            values.update({
                'existing_token': bool(tokens),
                'tokens': request.env['payment.token'],
            })
        return values


class PaymentPortal(payment_portal.PaymentPortal):

    # Payment overrides

    @route()
    def payment_pay(self, *args, invoice_id=None, **kwargs):
        """ Override of payment to replace the missing transaction values by that of the sale order.

        This is necessary for the reconciliation as all transaction values, excepted the amount,
        need to match exactly that of the sale order.

        :param str invoice_id: The account move for which a payment id made, as a `account.move` id
        :return: The result of the parent method
        :rtype: str
        :raise: ValidationError if the order id is invalid
        """
        # Cast numeric parameters as int or float and void them if their str value is malformed
        invoice_id = self.cast_as_int(invoice_id)
        if invoice_id:
            invoice_sudo = request.env['account.move'].browse(invoice_id).exists()
            if not invoice_sudo:
                raise ValidationError(_("The provided parameters are invalid."))

            kwargs['invoice_id'] = invoice_id
        return super().payment_pay(*args, **kwargs)

    def _get_custom_rendering_context_values(self, invoice_id=None, **kwargs):
        """ Return a dict of additional rendering context values.

        :param str invoice_id: The account move for which a payment id made, as a `account.move` id
        :param dict kwargs: Optional data. This parameter is not used here
        :return: The dict of additional rendering context values
        :rtype: dict
        """
        return {
            'invoice_id': invoice_id,
        }

    def _create_transaction(self, *args, invoice_id=None, custom_create_values=None, **kwargs):
        """ Override of payment to add the invoice id in the custom create values.

        :param int invoice_id: The account move for which a payment id made, as an `account.move` id
        :param dict custom_create_values: Additional create values overwriting the default ones
        :return: The result of the parent method
        :rtype: recordset of `payment.transaction`
        """
        if invoice_id:
            if custom_create_values is None:
                custom_create_values = {}

            custom_create_values['invoice_ids'] = [Command.set([int(invoice_id)])]

        return super()._create_transaction(
            *args, invoice_id=invoice_id, custom_create_values=custom_create_values, **kwargs
        )
