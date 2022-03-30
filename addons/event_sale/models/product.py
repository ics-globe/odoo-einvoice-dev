# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    detailed_type = fields.Selection(selection_add=[
        ('event', 'Event Ticket'),
    ], ondelete={'event': 'set service'})

    @api.onchange('detailed_type')
    def _onchange_type_event(self):
        if self.detailed_type == 'event':
            self.invoice_policy = 'order'

    def _detailed_type_mapping(self):
        type_mapping = super()._detailed_type_mapping()
        type_mapping['event'] = 'service'
        return type_mapping

    def price_compute(self, price_type, uom=None, currency=None, company=None, date=False):
        override_price = self._context.get('event_ticket_override_price')
        if override_price is not None:
            company = company or self.env.company
            date = date or fields.Date.context_today(self)

            self = self.with_company(company)
            prices = dict.fromkeys(self.ids, 0.0)
            for template in self:
                price = override_price
                price_currency = template.currency_id

                if uom:
                    price = template.uom_id._compute_price(price, uom)

                # Convert from current user company currency to asked one
                # This is right cause a field cannot be in more than one currency
                if currency:
                    price = price_currency._convert(price, currency, company, date)

                prices[template.id] = price
            return prices
        return super(ProductTemplate, self).price_compute(price_type, uom=uom, currency=currency, company=company, date=date)


class Product(models.Model):
    _inherit = 'product.product'

    event_ticket_ids = fields.One2many('event.event.ticket', 'product_id', string='Event Tickets')

    def price_compute(self, price_type, uom=None, currency=None, company=None, date=False):
        override_price = self._context.get('event_ticket_override_price')
        if override_price is not None:
            company = company or self.env.company
            date = date or fields.Date.context_today(self)

            self = self.with_company(company)
            prices = dict.fromkeys(self.ids, 0.0)
            for product in self:
                price = override_price
                price_currency = product.currency_id

                if uom:
                    price = product.uom_id._compute_price(price, uom)

                # Convert from current user company currency to asked one
                # This is right cause a field cannot be in more than one currency
                if currency:
                    price = price_currency._convert(price, currency, company, date)

                prices[product.id] = price
            return prices
        return super(Product, self).price_compute(price_type, uom=uom, currency=currency, company=company, date=date)
