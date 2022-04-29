odoo.define("website_sale.tour_utils", function (require) {
    "use strict";
    
    const core = require("web.core");
    const _t = core._t;


    function goToCart(quantity = 1, position = "bottom") {
        return {
            content: _t("Go to cart"),
            trigger: `a:has(.my_cart_quantity:containsExact(${quantity}))`,
            position: position,
            run: "click",
        };
    }

    function selectPriceList(pricelist) {
        return [
            {
                content: "Click on pricelist dropdown",
                trigger: "div.o_pricelist_dropdown a[data-toggle=dropdown]",
            },
            {
                content: "Click on pricelist",
                trigger: `span:contains(${pricelist})`,
            },
        ]
    }
    function assertProductPrice(attribute, value, productName) {
        return {
            content: `The ${attribute} of the ${productName} is ${value}`,
            trigger: `div:contains("${productName}") [data-oe-expression="template_price_vals[\'${attribute}\']"] .oe_currency_value:contains("${value}")`,
            run: () => {}
        }
    }
    return {
        goToCart,
        selectPriceList,
        assertProductPrice
    };
});
