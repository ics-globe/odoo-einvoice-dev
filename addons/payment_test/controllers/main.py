# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class PaymentTestController(http.Controller):
    _simulation_url = '/payment/test/simulate_payment'

    @http.route(_simulation_url, type='json', auth='public')
    def test_simulate_payment(self, **data):
        """ Simulate the response of a payment request.

        :param dict data: The notification data built with fake objects.
        See `_process_notification_data`.
        :return: None
        """
        # Retrieve the tx and acquirer based on the tx reference included in the return url
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'test', data
        )
        acquirer_sudo = tx_sudo.acquirer_id

        if acquirer_sudo.capture_manually and data['status'] == 'done':
            data['status'] = 'authorized'

        data['customer_input'] = data['customer_input'][-4:]

        tx_sudo._handle_notification_data('test', data)

        # Redirect the user to the status page
        return request.redirect('/payment/status')
