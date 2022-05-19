odoo.define('website_sale.delivery.payment.express_form', require => {
    'use strict';


    const paymentExpressForm = require('payment.express_form');

    paymentExpressForm.include({
        /**
         * TODO VCR DOCSTRING
         */
         _isShippingInformationRequired: function () {
            return true;
        },
    });
});