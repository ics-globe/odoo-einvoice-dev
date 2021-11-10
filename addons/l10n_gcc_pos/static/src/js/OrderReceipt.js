odoo.define('l10n_gcc_pos.OrderReceipt', function (require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt')
    const Registries = require('point_of_sale.Registries');

    const OrderReceiptGCC = OrderReceipt =>
        class extends OrderReceipt {
            constructor() {
                if (['SA', 'AE', 'BH', 'OM', 'QA', 'KW'].includes(arguments[1].order.pos.company.country.code)) {
                    OrderReceipt.template = 'l10n_gcc_pos.ArabicEnglishOrderReceipt';
                }
                super(...arguments);
            }
        }
    Registries.Component.extend(OrderReceipt, OrderReceiptGCC)
    return OrderReceiptGCC
});
