/** @odoo-module alias=mailing.PortalBlacklist **/

import core from 'web.core';
import publicWidget from 'web.public.widget';

const _t = core._t;


publicWidget.registry.MailingPortalBlacklist = publicWidget.Widget.extend({
    events: {
        'click #button_blacklist_add': '_onBlacklistAddClick',
        'click #button_blacklist_remove': '_onBlacklistRemoveClick',
    },

    /**
     * @override
     */
    init: function (parent, options) {
        console.log('MailingPortalBlacklist', parent, options);
        this.customer_data = options.customer_data;
        return this._super.apply(this, arguments);
    },

    /**
     * @override
     */
    start: function () {
        this._updateDisplay();
        return this._super.apply(this, arguments);
    },

    /*
     * Triggers call to add current email in blacklist. Update widget internals
     * and DOM accordingly (buttons display mainly). Bubble up to let parent
     * handle returned result if necessary.
     */
    _onBlacklistAddClick: function () {
        console.log('prout add blacklist');
        const self = this;
        this._rpc({
            route: '/mailing/blacklist/add',
            params: {
                email: this.customer_data.email,
                mailing_id: this.customer_data.mailingId,
                res_id: this.customer_data.documentId,
                token: this.customer_data.token,
            }
        }).then(function (result) {
            console.log('blacklist add', result);
            if (result === true) {
                self.customer_data.isBlacklisted = true;
            }
            self._updateDisplay()
            self.trigger_up('blacklist_add',
                            {'call_key': result === true ? 'blacklist_add' : result,
                             'is_blacklisted': result === true ? true: this.customer_data.isBlacklisted,
                            },
                           );
        });
    },

    /*
     * Triggers call to remove current email in blacklist. Update widget internals
     * and DOM accordingly (buttons display mainly). Bubble up to let parent
     * handle returned result if necessary.
     */
    _onBlacklistRemoveClick: function () {
        console.log('prout remove blacklist');
        const self = this;
        this._rpc({
            route: '/mailing/blacklist/remove',
            params: {
                email: this.customer_data.email,
                mailing_id: this.customer_data.mailingId,
                res_id: this.customer_data.documentId,
                token: this.customer_data.token,
            }
        }).then(function (result) {
            console.log('blacklist remove', result);
            if (result === true) {
                self.customer_data.isBlacklisted = false;
            }
            self._updateDisplay()
            self.trigger_up('blacklist_add',
                            {'call_key': result === true ? 'blacklist_remove' : result,
                             'is_blacklisted': result === true ? false: this.customer_data.isBlacklisted,
                            },
                           );
        });
    },

    /*
     * Display buttons according to current state
     */
    _updateDisplay: function () {
        console.log('updating with', this.customer_data);
        if (this.customer_data.blacklistEnabled && this.customer_data.blacklistPossible && !this.customer_data.isBlacklisted) {
            this.$('#button_blacklist_add').show();
        }
        else {
            this.$('#button_blacklist_add').hide();
        }
        if (this.customer_data.isBlacklisted) {
            this.$('#button_blacklist_remove').show();
        }
        else {
            this.$('#button_blacklist_remove').hide();
        }
    },
});

export default publicWidget.registry.MailingPortalSubscription;
