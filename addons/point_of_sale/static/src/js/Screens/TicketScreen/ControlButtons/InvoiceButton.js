odoo.define('point_of_sale.InvoiceButton', function (require) {
    'use strict';

    const { useListener } = require("@web/core/utils/hooks");
    const { isConnectionError } = require('point_of_sale.utils');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class InvoiceButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this._onClick);
        }
        get isAlreadyInvoiced() {
            if (!this.props.order) return false;
            return Boolean(this.props.order.account_move);
        }
        get commandName() {
            if (!this.props.order) {
                return this.env._t('Invoice');
            } else {
                return this.isAlreadyInvoiced
                    ? this.env._t('Reprint Invoice')
                    : this.props.order.isFromClosedSession
                    ? this.env._t('Cannot Invoice')
                    : this.env._t('Invoice');
            }
        }
        async _downloadInvoice(orderId) {
            try {
                // IMPROVEMENT: Use orm.read, but need a way to pass "load = false" as kwargs.
                const [orderWithInvoice] = await this.env.services.orm.call('pos.order', 'read', [orderId, ['account_move']], { load: false });
                if (orderWithInvoice && orderWithInvoice.account_move) {
                    await this.env.legacyActionManager.do_action('account.account_invoices', {
                        additional_context: {
                            active_ids: [orderWithInvoice.account_move],
                        },
                    });
                }
            } catch (error) {
                if (error instanceof Error) {
                    throw error;
                } else {
                    // NOTE: error here is most probably undefined
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Unable to download invoice.'),
                    });
                }
            }
        }
        async _invoiceOrder() {
            const order = this.props.order;
            if (!order) return;

            const orderId = order.backendId;

            // Part 0.1. If already invoiced, print the invoice.
            if (this.isAlreadyInvoiced) {
                await this._downloadInvoice(orderId);
                return;
            }

            // Part 0.2. Check if order belongs to an active session.
            // If not, do not allow invoicing.
            if (order.isFromClosedSession) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Session is closed'),
                    body: this.env._t('Cannot invoice order from closed session.'),
                });
                return;
            }

            // Part 1: Handle missing partner.
            // Write to pos.order the selected partner.
            if (!order.get_partner()) {
                const { confirmed: confirmedPopup } = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Need customer to invoice'),
                    body: this.env._t('Do you want to open the customer list to select customer?'),
                });
                if (!confirmedPopup) return;

                const { confirmed: confirmedTempScreen, payload: newPartner } = await this.showTempScreen(
                    'PartnerListScreen'
                );
                if (!confirmedTempScreen) return;

                await this.env.services.orm.write('pos.order', [orderId], { partner_id: newPartner.id });
            }

            // Part 2: Invoice the order.
            await this.env.services.orm.call('pos.order', 'action_pos_order_invoice', [orderId]);

            // Part 3: Download invoice.
            await this._downloadInvoice(orderId);
            this.trigger('order-invoiced', orderId);
        }
        async _onClick() {
            try {
                await this._invoiceOrder();
            } catch (error) {
                if (isConnectionError(error)) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Unable to invoice order.'),
                    });
                } else {
                    throw error;
                }
            }
        }
    }
    InvoiceButton.template = 'InvoiceButton';
    Registries.Component.add(InvoiceButton);

    return InvoiceButton;
});
