odoo.define('pos_discount.DiscountButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    class DiscountButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
        async onClick() {
            var self = this;
            const { confirmed, payload } = await this.showPopup('NumberPopup',{
                title: this.env._t('Discount Percentage'),
                startingValue: this.env.pos.config.discount_pc,
                isInputSelected: true
            });
            if (confirmed) {
                const val = Math.round(Math.max(0,Math.min(100,parseFloat(payload))));
                await self.apply_discount(val);
            }
        }

        async apply_discount(pc) {
            var order    = this.env.pos.get_order();
            var lines    = order.get_orderlines();
            var product  = this.env.pos.db.get_product_by_id(this.env.pos.config.discount_product_id[0]);
            if (product === undefined) {
                await this.showPopup('ErrorPopup', {
                    title : this.env._t("No discount product found"),
                    body  : this.env._t("The discount product seems misconfigured. Make sure it is flagged as 'Can be Sold' and 'Available in Point of Sale'."),
                });
                return;
            }

            // Remove existing discounts
            lines.filter(line => line.get_product().default_code === 'DISC')
                .forEach(line => order.remove_orderline(line));

            // Add one discount line per tax group
            let linesByTax = order.get_orderlines_grouped_by_tax_ids();
            for (let [taxIds, lines] of Object.entries(linesByTax)) {
                // Note that taxIdsArray is an Array of taxIds that apply to these lines
                // That is, the use case of products with more than one tax is supported.
                let taxIdsArray = taxIds.split(',').map(id => Number(id));

                // Consider price_include taxes use case
                let hasTaxesIncludedInPrice = taxIdsArray.filter(taxId =>
                    this.env.pos.taxes_by_id[taxId].price_include
                ).length;

                let _getTotalTaxesIncludedInPrice = line =>
                    line.get_taxes()
                        .filter(tax => tax.price_include)
                        .reduce((sum, tax) => sum + line.get_tax_details()[tax.id],
                        0
                    )
                
                let baseToDiscount = lines.reduce((sum, line) =>
                        sum +
                        line.get_price_without_tax() +
                        (hasTaxesIncludedInPrice ? _getTotalTaxesIncludedInPrice(line) : 0),
                    0
                );
            
                // We add the price as manually set to avoid recomputation when changing customer.
                let discount = - pc / 100.0 * baseToDiscount;
                if (discount < 0) {
                    order.add_product(product, {
                        price: discount,
                        lst_price: discount,
                        tax_ids: taxIdsArray,
                        merge: false,
                        description: _.str.sprintf(
                            this.env._t('tax: %s'),
                            taxIdsArray.map(taxId => this.env.pos.taxes_by_id[taxId].amount + '%').join(', ')
                        ),
                        extras: {
                            price_manually_set: true,
                        },
                    });
                }
            }
        }
    }
    DiscountButton.template = 'DiscountButton';

    ProductScreen.addControlButton({
        component: DiscountButton,
        condition: function() {
            return this.env.pos.config.module_pos_discount && this.env.pos.config.discount_product_id;
        },
    });

    Registries.Component.add(DiscountButton);

    return DiscountButton;
});
