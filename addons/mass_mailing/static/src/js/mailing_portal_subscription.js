/** @odoo-module alias=mailing.PortalSubscription **/

import core from 'web.core';
import publicWidget from 'web.public.widget';

const _t = core._t;


publicWidget.registry.MailingPortalSubscription = publicWidget.Widget.extend({
    custom_events: {
        'blacklist_add': '_onBlacklistAdd',
        'blacklist_remove': '_onBlacklistRemove',
    },
    selector: '#o_mailing_subscription',

    /**
     * @override
     */
    start: function () {
        this.customer_data = this.$el.data();
        this.$subscription_info = this.$('#o_mailing_subscription_info');
        this.$subscription_info_message = this.$('#o_mailing_subscription_info_message');
        this.$subscription_list_manage = this.$('.o_mailing_subscription_list_manage');
        this._attachBlacklist();
        this._updateDisplay();
        return this._super.apply(this, arguments);
    },

    _attachBlacklist: function () {
        const $bl_elem = this.$('.o_mailing_blacklist');
        console.log($bl_elem);
        if ($bl_elem.length) {
            this.mailingPortalBlacklistWidget = new publicWidget.registry.MailingPortalBlacklist(
                this,
                {customer_data: this.customer_data}
            );
            this.mailingPortalBlacklistWidget.attachTo($bl_elem);
        }
    },

    _onBlacklistAdd: function (event) {
        const call_key = event.data.call_key;
        this.customer_data.isBlacklisted = event.data.isBlacklisted;
        console.log('blacklist add', event, call_key, 'is bl', this.customer_data.isBlacklisted);
        this._updateDisplay();
        this._updateSubscriptionInfo(call_key);
    },

    _onBlacklistRemove: function (event) {
        const call_key = event.data.call_key;
        console.log('blacklist remove', event, call_key);
        this._updateDisplay();
        this._updateSubscriptionInfo(call_key);
    },

    _updateDisplay: function () {
        if (this.customer_data.isBlacklisted) {
            this.$subscription_list_manage.find('input').attr('disabled', 'disabled');
        }
        else {
            this.$subscription_list_manage.find('input').attr('disabled', undefined);
        }
    },

    _updateSubscriptionInfo: function (call_key) {
        if (call_key == 'blacklist_add') {
            this.$subscription_info_message.text(
                _t('You have been successfully added to our blacklist. You will not be contacted anymore by our services.')
            );
            this.$subscription_info.removeClass('alert-error alert-warning').addClass('alert-success');
        }
        else if (call_key == 'blacklist_remove') {
            this.$subscription_info_message.text(
                _t('You have been successfully removed from our blacklist. You are now able to be contacted by our services.')
            );
            this.$subscription_info.removeClass('alert-error alert-warning').addClass('alert-success');
        }
        else if (call_key == 'unauthorized') {
            this.$subscription_info_message.text(
                _t('You are not authorized to do this.')
            );
            this.$subscription_info.removeClass('alert-success alert-warning').addClass('alert-error');
        }
        else {
            this.$subscription_info_message.text(
                _t('An error occurred. Please try again later or contact us.')
            );
            this.$subscription_info.removeClass('alert-success alert-warning').addClass('alert-error');
        }
    },
});

export default publicWidget.registry.MailingPortalSubscription;
