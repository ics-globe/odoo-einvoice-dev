# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteEventSale(WebsiteSale):

    def _prepare_confirmation_values(self, order):
        values = super(WebsiteEventSale,
                       self)._prepare_confirmation_values(order)
        if any(line.product_id.detailed_type == 'event' for line in order.order_line):
            events = order.order_line.event_id
            if events:
                values['events'] = events
        return values
