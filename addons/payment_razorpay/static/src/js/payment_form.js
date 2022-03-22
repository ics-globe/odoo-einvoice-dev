/* global Razorpay */
odoo.define('payment_razorpay.payment_form', require => {
    'use strict';

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const razorpayMixin = {

        /**
         * Redirect the customer to Razorpay hosted payment page.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the payment option's acquirer
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {undefined}
         */
        _processRedirectPayment(provider, paymentOptionId, processingValues) {
            if (provider !== 'razorpay') {
                return this._super(...arguments);
            }
            const razorpayOptions = this._prepareRazorpayOptions(processingValues);
            const rzp = Razorpay(razorpayOptions);
            rzp.open();
            rzp.on('payment.failed',(resp) => {
                alert(resp.error.code);
                alert(resp.error.description);
                alert(resp.error.source);
                alert(resp.error.step);
                alert(resp.error.reason);
                alert(resp.error.metadata.order_id);
                alert(resp.error.metadata.payment_id);
        });
        },
        /**
         * Prepare the options to init the RazorPay JS Object
         *
         * Function overriden in internal module
         *
         * @param {object} processingValues
         * @return {object}
         */
        _prepareRazorpayOptions(processingValues) {
            return Object.assign({}, processingValues, {
                "handler": (resp) => {
                    const razorpayPaymentId = resp.razorpay_payment_id;
                    const razorpayOrderId = resp.razorpay_order_id;
                    const razorpaySubscriptionId = resp.razorpay_subscription_id
                    const razorpaySignature = resp.razorpay_signature

                    if (razorpayPaymentId && (razorpayOrderId || razorpaySubscriptionId) && razorpaySignature) {
                        $.post('/payment/razorpay/capture',{
                            razorpay_payment_id: razorpayPaymentId,
                            razorpay_order_id: razorpayOrderId || false,
                            razorpay_subscription_id : razorpaySubscriptionId || false,
                            razorpay_signature: razorpaySignature,
                        }).done((data) => {
                            window.location.href = data;
                        }).fail((data) => {
                            window.location.href = data;
                        });
                    }
                },
            });
        },
    };

    checkoutForm.include(razorpayMixin);
    manageForm.include(razorpayMixin);
});
