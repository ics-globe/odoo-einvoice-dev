# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.tools.float_utils import float_repr, float_round
from odoo.addons.payment.models.payment_acquirer import ValidationError


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('razorpay', 'Razorpay')])
    razorpay_key_id = fields.Char(string='Key ID', required_if_provider='razorpay', groups='base.group_user')
    razorpay_key_secret = fields.Char(string='Key Secret', required_if_provider='razorpay', groups='base.group_user')

    def razorpay_form_generate_values(self, values):
        self.ensure_one()
        currency = self.env['res.currency'].sudo().browse(values['currency_id'])
        if currency != self.env.ref('base.INR'):
            raise ValidationError(_('Currency not supported by Razorpay'))
        values.update({
            'key': self.razorpay_key_id,
            'amount': float_repr(float_round(values.get('amount'), 2) * 100, 0),
            'name': values.get('partner_name'),
            'contact': values.get('partner_phone'),
            'email': values.get('partner_email'),
            'order_id': values.get('reference'),
        })
        return values
