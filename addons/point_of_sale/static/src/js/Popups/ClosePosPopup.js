odoo.define('point_of_sale.ClosePosPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { isConnectionError } = require('point_of_sale.utils');

    const { onWillStart, onMounted, useState } = owl;

    /**
     * This popup needs to be self-dependent because it needs to be called from different place.
     */
    class ClosePosPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.manualInputCashCount = false;
            this.cashControl = this.env.pos.config.cash_control;
            this.closeSessionClicked = false;
            this.moneyDetails = null;
            this.state = useState({
                displayMoneyDetailsPopup: false,
            });
            onWillStart(this.onWillStart);
            onMounted(this.onMounted);
        }
        async onWillStart() {
            try {
                const closingData = await this.env.services.orm.call('pos.session', 'get_closing_control_data', [[this.env.pos.pos_session.id]]);
                this.ordersDetails = closingData.orders_details;
                this.paymentsAmount = closingData.payments_amount;
                this.payLaterAmount = closingData.pay_later_amount;
                this.openingNotes = closingData.opening_notes;
                this.defaultCashDetails = closingData.default_cash_details;
                this.otherPaymentMethods = closingData.other_payment_methods;
                this.isManager = closingData.is_manager;
                this.amountAuthorizedDiff = closingData.amount_authorized_diff;

                // component state and refs definition
                const state = {notes: '', acceptClosing: false, payments: {}};
                if (this.cashControl) {
                    state.payments[this.defaultCashDetails.id] = {counted: 0, difference: -this.defaultCashDetails.amount, number: 0};
                }
                if (this.otherPaymentMethods.length > 0) {
                    this.otherPaymentMethods.forEach(pm => {
                        if (pm.type === 'bank') {
                            state.payments[pm.id] = {counted: this.env.pos.round_decimals_currency(pm.amount), difference: 0, number: pm.number}
                        }
                    })
                }
                Object.assign(this.state, state);
            } catch (error) {
                this.error = error;
            }
        }
        /*
         * Since this popup need to be self dependent, in case of an error, the popup need to be closed on its own.
         */
        onMounted() {
            if (this.error) {
                this.cancel();
                if (isConnectionError(this.error)) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Please check your internet connection and try again.'),
                    });
                } else {
                    throw this.error;
                }
            }
        }
        openDetailsPopup() {
            this.state.payments[this.defaultCashDetails.id].counted = 0;
            this.state.payments[this.defaultCashDetails.id].difference = -this.defaultCashDetails.amount;
            this.state.notes = "";
            this.state.displayMoneyDetailsPopup = true;
        }
        closeDetailsPopup() {
            this.state.displayMoneyDetailsPopup = false;
        }
        handleInputChange(paymentId) {
            let expectedAmount;
            if (paymentId === this.defaultCashDetails.id) {
                this.manualInputCashCount = true;
                this.state.notes = '';
                expectedAmount = this.defaultCashDetails.amount;
            } else {
                expectedAmount = this.otherPaymentMethods.find(pm => paymentId === pm.id).amount;
            }
            this.state.payments[paymentId].difference =
                this.env.pos.round_decimals_currency(this.state.payments[paymentId].counted - expectedAmount);
            this.state.acceptClosing = false;
        }
        updateCountedCash({ total, moneyDetailsNotes, moneyDetails }) {
            this.state.payments[this.defaultCashDetails.id].counted = total;
            this.state.payments[this.defaultCashDetails.id].difference =
                this.env.pos.round_decimals_currency(this.state.payments[[this.defaultCashDetails.id]].counted - this.defaultCashDetails.amount);
            if (moneyDetailsNotes) {
                this.state.notes = moneyDetailsNotes;
            }
            this.manualInputCashCount = false;
            this.moneyDetails = moneyDetails;
            this.state.acceptClosing = false;
            this.closeDetailsPopup();
        }
        hasDifference() {
            return Object.entries(this.state.payments).find(pm => pm[1].difference != 0);
        }
        hasUserAuthority() {
            const absDifferences = Object.entries(this.state.payments).map(pm => Math.abs(pm[1].difference));
            return this.isManager || this.amountAuthorizedDiff == null || Math.max(...absDifferences) <= this.amountAuthorizedDiff;
        }
        canCloseSession() {
            return !this.cashControl || !this.hasDifference() || this.state.acceptClosing;
        }
        canCancel() {
            return true;
        }
        cancelPopup() {
            if (this.canCancel()) {
                this.cancel();
            }
        }
        closePos() {
            this.trigger('close-pos');
        }
        async closeSession() {
            if (this.canCloseSession() && !this.closeSessionClicked) {
                this.closeSessionClicked = true;
                let response;
                if (this.cashControl) {
                    response = await this.env.services.orm.call(
                        'pos.session',
                        'post_closing_cash_details',
                        [this.env.pos.pos_session.id],
                        {
                            counted_cash: this.state.payments[this.defaultCashDetails.id].counted,
                        }
                    );
                    if (!response.successful) {
                        return this.handleClosingError(response);
                    }
                }
                await this.env.services.orm.call('pos.session', 'update_closing_control_state_session', [
                    this.env.pos.pos_session.id,
                    this.state.notes,
                ]);
                try {
                    const bankPaymentMethodDiffPairs = this.otherPaymentMethods
                        .filter((pm) => pm.type == 'bank')
                        .map((pm) => [pm.id, this.state.payments[pm.id].difference]);
                    response = await this.env.services.orm.call('pos.session', 'close_session_from_ui', [
                        this.env.pos.pos_session.id,
                        bankPaymentMethodDiffPairs,
                    ]);
                    if (!response.successful) {
                        return this.handleClosingError(response);
                    }
                    window.location = '/web#action=point_of_sale.action_client_pos_menu';
                } catch (error) {
                    if (isConnectionError(error)) {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Network Error'),
                            body: this.env._t('Cannot close the session when offline.'),
                        });
                    } else {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t('Closing session error'),
                            body: this.env._t(
                                'An error has occurred when trying to close the session.\n' +
                                'You will be redirected to the back-end to manually close the session.')
                        })
                        window.location = '/web#action=point_of_sale.action_client_pos_menu';
                    }
                }
                this.closeSessionClicked = false;
            }
        }
        async handleClosingError(response) {
            await this.showPopup('ErrorPopup', {title: 'Error', body: response.message});
            if (response.redirect) {
                window.location = '/web#action=point_of_sale.action_client_pos_menu';
            }
        }
        _getShowDiff(pm) {
            return pm.type == 'bank' && pm.number !== 0;
        }
    }

    ClosePosPopup.template = 'ClosePosPopup';
    Registries.Component.add(ClosePosPopup);

    return ClosePosPopup;
});
