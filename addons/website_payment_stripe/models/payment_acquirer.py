# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, fields, models
from werkzeug import urls


_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    domain_registered = fields.Boolean()  # TODO VCR: False when we made any change to the domain name + Add String, help all things needed

    def action_stripe_link_apple_domain(self):
        """ Registered a domain for the usage of Apple Pay

        Note: This action only works for instances using a public URL

        :return: The feedback notification
        :rtype: dict
        """
        self.ensure_one()

        # TODO VCR: Apple Pay can only be registered with production keys. When we will separate
        # test credentials and production credentials, ensure that the check is made on the
        # production credentials.
        if not self.stripe_secret_key:
            message = _("You cannot create a Stripe Webhook if your Stripe Secret Key is not set.")
            notification_type = 'danger'
        else:
            base_domain = urls.url_parse(self.get_base_url()).netloc
            _logger.info(
                "Registering domain for Apple Pay  on Stripe:\n%s", pprint.pformat(base_domain)
            )
            self._stripe_make_request(
                'apple_pay/domains', payload={
                    'domain_name': base_domain
                }
            )
            self.domain_registered = True
            message = _("You domain was successfully registered!")
            notification_type = 'info'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'sticky': False,
                'type': notification_type,
                'next': {'type': 'ir.actions.act_window_close'},  # Refresh the form to hide the button
            }
        }
