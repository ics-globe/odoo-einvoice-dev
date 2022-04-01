/** @odoo-module **/

import {WebsiteSale} from 'website_sale.website_sale';
import VariantMixin from "sale.VariantMixin";
import wSaleUtils from 'website_sale.utils';
import {is_email} from 'web.utils';

WebsiteSale.include({

    events: Object.assign({}, WebsiteSale.prototype.events, {
        'click #add_stock_email_notification_product_message': '_onClickAddStockEmailNotificationProductMessage',
        'click #add_stock_email_notification_product_form_button': '_onSubmitAddStockEmailNotificationProductForm',
    }),

    _onClickAddStockEmailNotificationProductMessage: function (ev) {
        ev.currentTarget.classList.add('d-none');
        const partner_email = document.querySelector('#partner_email').value;
        const form = ev.currentTarget.parentElement.querySelector('#add_stock_email_notification_product_form');
        const email_input = form.querySelector('input[name="email"]');

        email_input.value = partner_email;
        form.classList.remove('d-none');

    },

    _onSubmitAddStockEmailNotificationProductForm: function (ev) {
        const self = this;
        const form = ev.currentTarget.closest('#add_stock_email_notification_product_form');
        const product_id = parseInt(form.querySelector('input[name="product_id"]').value);
        const email = form.querySelector('input[name="email"]').value.trim();
        const incorrect_icon = form.querySelector('#add_stock_email_notification_product_input_incorrect');
        if (!is_email(email)) {
            incorrect_icon.classList.remove('d-none');
            return
        }

        this._rpc({
            route: "/shop/add_stock_email_notification",
            params: {
                product_id,
                email
            },
        }).then(function (data) {
            if (data === '400 Bad Request: Invalid Email'){
                incorrect_icon.classList.remove('d-none');
                return
            }
            const div = form.closest('#add_stock_email_notification_product_div');
            const message = div.querySelector('#add_stock_email_notification_product_success_message');

            message.classList.remove('d-none');
            form.classList.add('d-none');

            // This is to add the product to the wishlist since it creates one.
            // We have to check that website_sale_wishlist is installed to add it.
            if (self.wishlistProductIDs && !self.wishlistProductIDs.includes(product_id)) {
                self.wishlistProductIDs.push(product_id);
                self._updateWishlistView();
                const $navButton = $('header .o_wsale_my_wish').first();
                wSaleUtils.animateClone($navButton, $(ev.currentTarget.closest('form')), 25, 40);
                const save_for_later_button = document.querySelector('#save_for_later_button');
                const added_to_your_wishlist_alert = document.querySelector('#added_to_your_wishlist_alert');

                if (save_for_later_button) {
                    save_for_later_button.classList.add('d-none');
                    added_to_your_wishlist_alert.classList.remove('d-none');
                }
            }
        });
    },
    /**
     * Adds the stock checking to the regular _onChangeCombination method
     * @override
     */
    _onChangeCombination: function () {
        this._super.apply(this, arguments);
        VariantMixin._onChangeCombinationStock.apply(this, arguments);
    },
    /**
     * Recomputes the combination after adding a product to the cart
     * @override
     */
    _onClickAdd(ev) {
        return this._super.apply(this, arguments).then(() => {
            if ($('div.availability_messages').length) {
                this._getCombinationInfo(ev);
            }
        });
    }
});
