/** @odoo-module **/

import {WebsiteSale} from 'website_sale.website_sale';
import {is_email} from 'web.utils';

WebsiteSale.include({
    events: Object.assign({}, WebsiteSale.prototype.events, {
        'click #add_stock_email_notification_wishlist_button': '_onClickAddStockEmailNotificationWishlistMessage',
        'click #add_stock_email_notification_wishlist_form_button': '_onSubmitAddStockEmailNotificationWishlistForm',
    }),

    _onClickAddStockEmailNotificationWishlistMessage: function (ev) {
        //hide the message, display the input box
        ev.currentTarget.classList.add('d-none');
        const form = ev.currentTarget.parentElement.querySelector('#add_stock_email_notification_wishlist_form');

        form.classList.remove('d-none');

    },

    _onSubmitAddStockEmailNotificationWishlistForm: function (ev) {
        const form = ev.currentTarget.closest('#add_stock_email_notification_wishlist_form');
        const product_id = JSON.parse(ev.currentTarget.closest('tr').getAttribute('data-product-tracking-info')).item_id;
        const email = form.querySelector('input[name="email"]').value;
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
            const div = form.closest('#add_stock_email_notification_wishlist_div');
            const message = div.querySelector('#add_stock_email_notification_wishlist_success_message');

            message.classList.remove('d-none');
            form.classList.add('d-none')
        });
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Removes wishlist indication when adding a product to the wishlist.
     *
     * @override
     */
    _addNewProducts: function () {
        this._super(...arguments);
        const save_for_later_button = document.querySelector('#save_for_later_button');
        const added_to_your_wishlist_alert = document.querySelector('#added_to_your_wishlist_alert');

        if (save_for_later_button) {
            save_for_later_button.classList.add('d-none');
            added_to_your_wishlist_alert.classList.remove('d-none');
        }
    },
});
