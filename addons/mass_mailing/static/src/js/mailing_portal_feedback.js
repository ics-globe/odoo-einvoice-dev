/** @odoo-module alias=mailing.PortalFeedback **/

import core from 'web.core';
import publicWidget from 'web.public.widget';

const _t = core._t;


publicWidget.registry.MailingPortalFeedback = publicWidget.Widget.extend({
    events: {
        'click #button_feedback': '_onFeedbackClick',
    },

    /**
     * @override
     */
    init: function (parent, options) {
        console.log('MailingPortalFeedback', parent, options);
        this.customer_data = options.customer_data;
        return this._super.apply(this, arguments);
    },

    /*
     * Triggers call to add current email in blacklist. Update widget internals
     * and DOM accordingly (buttons display mainly). Bubble up to let parent
     * handle returned result if necessary.
     */
    _onFeedbackClick: function () {
        console.log('prout add blacklist');
        const self = this;
        const feedback = 'prout';
        this._rpc({
            route: '/mailing/feedback',
            params: {
                email: this.customer_data.email,
                feedback: feedback,
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
});

export default publicWidget.registry.MailingPortalFeedback;
