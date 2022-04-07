/* global Stripe */
odoo.define('payment_stripe.payment_form', require => {
    'use strict';

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');
    const expressForm = require('payment.express_form');

    const stripeMixin = {

        /**
         * Redirect the customer to Stripe hosted payment page.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the payment option's acquirer
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {undefined}
         */
        _processRedirectPayment: function (provider, paymentOptionId, processingValues) {
            if (provider !== 'stripe') {
                return this._super(...arguments);
            }

            const stripeJS = Stripe(processingValues['publishable_key'],
                this._prepareStripeOptions(processingValues));
            stripeJS.redirectToCheckout({
                sessionId: processingValues['session_id']
            });
        },

        /**
         * Prepare the options to init the Stripe JS Object
         *
         * Function overriden in internal module
         *
         * @param {object} processingValues
         * @return {object}
         */
        _prepareStripeOptions: function (processingValues) {
            return {};
        },
    };

    const stripeExpressMixin = {

        /**
         * Prepare the express form of Stripe for direct payment.
         *
         * @override method from payment.express_form
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @return {undefined}
         */
        _prepareExpressForm: function (provider, paymentOptionId) {
            if (provider !== 'stripe') {
                return this._super(...arguments);
            }

            // Check if instantiation of the drop-in is needed
            if (this.StripeExpress && this.StripeExpress.acquirerId === paymentOptionId) {
                this._setPaymentFlow('direct'); // Overwrite the flow even if no re-instantiation
                return Promise.resolve(); // Don't re-instantiate if already done for this acquirer
            }

            var self = this;
            self._rpc({
                // Create transaction
                route: '/payment/stripe/publishable_key',
                params: {acquirer_id:paymentOptionId},
            }).then(stripe_publishable_key => {
                const stripeJS = Stripe(stripe_publishable_key);
                var paymentRequest = stripeJS.paymentRequest({
                    country:'BE',
                    currency: this.txContext.currencyName,
                    total: {
                        label: this.txContext.label,
                        amount: this.txContext.minorAmount,
                    },
                    requestPayerName: true,
                    requestPayerEmail: true,
                    requestPayerPhone: true,

                    requestShipping: true,
                    // `shippingOptions` is optional at this point:
                    shippingOptions: [
                        // The first shipping option in this list appears as the default
                        // option in the browser payment interface.
                        {
                        id: 'free-shipping',
                        label: 'Free shipping',
                        detail: 'Arrives in 5 to 7 days',
                        amount: 0,
                        },
                    ],
                });
                self.StripeExpress = paymentRequest;
                self.StripeExpress.acquirerId = paymentOptionId;

                var elements = stripeJS.elements();
                var prButton = elements.create('paymentRequestButton', {
                    paymentRequest: paymentRequest,
                });

                // Check the availability of the Payment Request API first.
                paymentRequest.canMakePayment().then(function(result) {
                    if (result) {
                        prButton.mount(`#o_stripe_express_checkout_container_${paymentOptionId}`);
                    }
                });

                paymentRequest.on('paymentmethod', function(ev) {
                    // Send addresses
                    self._rpc({
                        route: '/shop/express/address',
                        params: {
                            billing: {
                                name: ev.payerName,
                                email: ev.payerEmail,
                                phone: ev.payerPhone,
                                street: ev.paymentMethod.billing_details.address.line1,
                                street2: ev.paymentMethod.billing_details.address.line2,
                                zip: ev.paymentMethod.billing_details.address.postal_code,
                                city: ev.paymentMethod.billing_details.address.city,
                                country: ev.paymentMethod.billing_details.address.country,
                                state: ev.paymentMethod.billing_details.address.state,
                            },
                            shipping: {
                                name: ev.shippingAddress.recipient,
                                phone: ev.shippingAddress.phone,
                                street: ev.shippingAddress.addressLine[0],
                                street2: ev.shippingAddress.addressLine[1],
                                zip: ev.shippingAddress.postalCode,
                                city: ev.shippingAddress.city,
                                country: ev.shippingAddress.country,
                                state: ev.shippingAddress.region,
                            },
                            partner_id: parseInt(self.txContext.partnerId),
                        }
                    }).then((partner_id) => {
                        self.txContext.partnerId = parseInt(partner_id)
                        self._rpc({
                            // Create transaction
                            route: self.txContext.transactionRoute,
                            params: self._prepareTransactionRouteParams(provider, paymentOptionId),
                        }).then(processingValues => {
                            // Confirm the PaymentIntent without handling potential next actions (yet).
                            stripeJS.confirmCardPayment(
                                processingValues.client_secret,
                                {payment_method: ev.paymentMethod.id},
                                {handleActions: false},
                            ).then(function(confirmResult) {
                                if (confirmResult.error) {
                                    // Report to the browser that the payment failed, prompting it to
                                    // re-show the payment interface, or show an error message and close
                                    // the payment interface.
                                    ev.complete('fail');
                                } else {
                                    // Report to the browser that the confirmation was successful, prompting
                                    // it to close the browser payment method collection interface.
                                    ev.complete('success');
                                    // Check if the PaymentIntent requires any actions and if so let Stripe.js
                                    // handle the flow. If using an API version older than "2019-02-11"
                                    // instead check for: `paymentIntent.status === "requires_source_action"`.
                                    if (confirmResult.paymentIntent.status === "requires_action") {
                                        // Let Stripe.js handle the rest of the payment flow.
                                        stripeJS.confirmCardPayment(processingValues.clientSecret).then(function(result) {
                                            if (result.error) {
                                                // The payment failed -- ask your customer for a new payment method.
                                            } else {
                                                // The payment has succeeded.
                                                window.location = '/payment/status';
                                            }
                                        });
                                    } else {
                                        // The payment has succeeded.
                                        window.location = '/payment/status';
                                    }
                                }
                            });
                        });
                    }).guardedCatch((error) => {
                        // TODO VCR: Handle errors
                    });
                });
            });
        },

        /**
         * TODO VCR: Docstring
         *
         * Prepare the express form of Stripe for direct payment.
         *
         * @override method from payment.express_form
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {number} newAmount - The new amount
         * @return {undefined}
         */
        _updateAmount: function (provider, paymentOptionId, newAmount, newMinorAmount) {
            if (provider !== 'stripe') {
                return this._super(...arguments);
            }
            // Check if the payment method is instanciated and if it is the right acquirer
            if (this.StripeExpress && this.StripeExpress.acquirerId === paymentOptionId) {
                this.txContext.amount = parseFloat(newAmount);
                this.txContext.minorAmount = parseInt(newMinorAmount);
                this.StripeExpress.update({
                    total: {
                      amount: parseInt(newMinorAmount),
                      label: this.txContext.label,
                    }
                });
            }
        },
    };

    checkoutForm.include(stripeMixin);
    manageForm.include(stripeMixin);
    expressForm.include(stripeExpressMixin);

});
