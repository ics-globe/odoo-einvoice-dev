# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http

from odoo.addons.payment_stripe.controllers.main import StripeController
from odoo.modules.module import get_resource_path


class WebsiteStripeController(StripeController):
    _apple_pay_url = '/.well-known/apple-developer-merchantid-domain-association'

    @http.route(_apple_pay_url, type='http', auth='public', csrf=False)
    def stripe_apple_pay(self):
        """_summary_
        """
        file_path = get_resource_path(
            'website_payment_stripe', 'static', 'apple-developer-merchantid-domain-association'
        )
        return open(file_path, 'rb').read()
