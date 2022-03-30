odoo.define('website_event_sale.ticket_price', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
const core = require('web.core');

/**
 * This widget fetch and renders the event ticket price and refresh it when an event "event_ticket_quantity_change" is
 * fired concerning the ticket given as parameter.
 * @param: {integer} ticketId id of the ticket for which the price will be rendered
 */
const EventSaleTicketPriceWidget = publicWidget.Widget.extend({
    template: 'website_event_sale.event_ticket_price',
    xmlDependencies: ['/website_event_sale/static/src/xml/website_event_sale_ticket_price.xml'],
    selector: '.o_event_sale_ticket_price',
    events: {},

    start: function () {
        return this._super.apply(this, arguments).then(() => {
            this.ticketId = this.$el.data('ticketId');
            this.ready = false;
            this.data = null;
            core.bus.on('event_ticket_quantity_change', this, this._quantity_change);
            return this._update(0);
        });
    },

    _quantity_change: function(data) {
        if (data.ticketId === this.ticketId) {
            this._update(data.quantity);
        }
    },

    render_monetary_field: function(value, currency) {
        let formatted_value = value.toFixed(currency.decimal_places);
        if (currency.position === "after") {
            formatted_value += currency.symbol;
        } else {
            formatted_value = currency.symbol + formatted_value;
        }
        return formatted_value;
    },

    _update: function(quantity) {
        return this._rpc({
                route: `/website_event_sale/ticket-price-info/${this.ticketId}`,
                params: { quantity:quantity },
            }).then(data => {
                this.data = data;
                this.ready = true;
                this.renderElement();
            });
    },

});

publicWidget.registry.EventSaleTicketPrice = EventSaleTicketPriceWidget;

return EventSaleTicketPriceWidget;

});
