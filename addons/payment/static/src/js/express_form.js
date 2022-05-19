odoo.define('payment.express_mixin', require => {
    'use strict';

    const core = require('web.core');

    return {

        /**
         * @override
         */
        start: async function () {
            await this._super(...arguments);
            window.addEventListener('pageshow', function (event) {
                if (event.persisted) {
                    window.location.reload();
                }
            });
            this.txContext = {};
            Object.assign(this.txContext, this.$el.data());
            this.txContext.flow = 'direct';
            const $expressForm = this.$('input[name="o_payment_express"]');
            this._displayExpressForm($expressForm[0]);
            core.bus.on('amount_changed', this, this._updateAllAmount);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Display the express form of the availaible payment acquirer.
         *
         * @private
         * @param {HTMLInputElement} expressForm - The form linked to the payment option
         * @return {undefined}
         */
         _displayExpressForm: function (expressForm) {
            // Extract contextual values from the radio button
            const provider = this._getProviderFromExpressForm(expressForm);
            const paymentOptionId = this._getPaymentOptionIdFromExpressForm(expressForm);
            // Prepare the inline form of the selected payment option and display it if not empty
            this._prepareExpressForm(provider, paymentOptionId);
        },

        /**
         * Determine and return the id of the selected payment option.
         *
         * @private
         * @param {HTMLInputElement} expressForm - The form linked to the payment option
         * @return {number} The acquirer id of the payment option linked to the form.
         */
         _getPaymentOptionIdFromExpressForm: expressForm => $(expressForm).data('payment-option-id'),

         /**
          * Determine and return the provider of the selected payment option.
          *
          * @private
          * @param {HTMLInputElement} expressForm - The form linked to the payment option
          * @return {number} The provider of the payment option linked to the form.
          */
         _getProviderFromExpressForm: expressForm => $(expressForm).data('provider'),

        /**
         * Prepare the acquirer-specific express form of the selected payment option.
         *
         * For an acquirer to manage an express form, it must override this method. When the
         * override is called, it must lookup the parameters to decide whether it is necessary
         * to prepare its express form. Otherwise, the call must be sent back to the parent method.
         *
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @return {Promise}
         */
        _prepareExpressForm: (provider, paymentOptionId) => Promise.resolve(),

        /**
         * TODO VCR: Docstring
         *
         * @override method from payment.express_form
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option.
         * @param {number} newAmount - The new amount
         * @return {undefined}
         */
        _updateAllAmount: function (newAmount, newMinorAmount, expressForm=false) {
            // Extract contextual values from the radio button
            if (!expressForm) {
                expressForm = document.getElementsByName("o_payment_express");
            }
            const provider = this._getProviderFromExpressForm(expressForm);
            const paymentOptionId = this._getPaymentOptionIdFromExpressForm(expressForm);
            // Prepare the inline form of the selected payment option and display it if not empty
            this._updateAmount(provider, paymentOptionId, newAmount, newMinorAmount);
        },

        /**
         * TODO VCR: Docstring
         *
         * @override method from payment.express_form
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option.
         * @param {number} newAmount - The new amount
         * @return {undefined}
         */
        _updateAmount: (provider, paymentOptionId, newAmount, newMinorAmount) => Promise.resolve(),

        /**
         * Prepare the params to send to the transaction route.
         *
         * For an acquirer to overwrite generic params or to add acquirer-specific ones, it must
         * override this method and return the extended transaction route params.
         *
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @return {object} The transaction route params
         */
        _prepareTransactionRouteParams: function (provider, paymentOptionId) {
            return {
                'payment_option_id': paymentOptionId,
                'reference_prefix': this.txContext.referencePrefix !== undefined
                    ? this.txContext.referencePrefix.toString() : null,
                'amount': this.txContext.amount !== undefined
                    ? parseFloat(this.txContext.amount) : null,
                'currency_id': this.txContext.currencyId
                    ? parseInt(this.txContext.currencyId) : null,
                'partner_id': parseInt(this.txContext.partnerId),
                'flow': 'direct',
                'tokenization_requested': false,
                'landing_route': this.txContext.landingRoute,
                'add_id_to_landing_route': true,
                'access_token': this.txContext.accessToken
                    ? this.txContext.accessToken : undefined,
                'csrf_token': core.csrf_token,
            };
        },

        /**
         * TODO VCR DOCSTRING
         */
        _isShippingInformationRequired: function () {
            return false;
        },
    };

});

odoo.define('payment.express_form', require => {
    'use strict';

    const publicWidget = require('web.public.widget');

    const paymentExpressMixin = require('payment.express_mixin');

    publicWidget.registry.PaymentExpressForm = publicWidget.Widget.extend(paymentExpressMixin, {
        selector: 'form[name="o_payment_express_checkout"]',
    });

    return publicWidget.registry.PaymentExpressForm;
});
