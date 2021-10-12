/** @odoo-module **/

import publicWidget from 'web.public.widget';
import '@website_slides/js/slides';
import { _t } from 'web.core';

var ShareMail = publicWidget.Widget.extend({
    events: {
        'click button': '_sendMail',
        'keypress input': '_onKeypress',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Send the email(s) on 'Enter' key
     *
     * @private
     * @param {Event} ev
     */
    _onKeypress: function (ev) {
        if (ev.keyCode === $.ui.keyCode.ENTER) {
            ev.preventDefault();
            this._sendMail();
        }
    },

    _sendMail: function () {
        var self = this;
        const channelID = this.$('button').data('channel-id');
        var input = this.$('input');
        var slideID = this.$('button').data('slide-id');
        let resID;
        let resModel;
        let route;
        if (slideID) {
            resID = slideID;
            resModel = 'slide.slide'
            route = '/slides/send_share_email';
        } else if (channelID) {
            resID = channelID;
            resModel = 'slide.channel'
            route = '/slides/send_share_email';
        }
        if (input.val()) {
            this.$el.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
            this._rpc({
                route: route,
                params: {
                    emails: input.val(),
                    res_id: resID,
                    res_model: resModel,
                },
            }).then((action) => {
                if (action) {
                    self.$('.alert-info').removeClass('d-none');
                    self.$('.input-group').addClass('d-none');
                } else {
                    self.displayNotification({ message: _t('Please enter valid email(s)'), type: 'danger' });
                    self.$el.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
                    input.focus();
                }
            });
        } else {
            this.displayNotification({ message: _t('Please enter valid email(s)'), type: 'danger' });
            this.$el.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
            input.focus();
        }
    },
});

publicWidget.registry.websiteSlidesShare = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click a.o_wslides_js_social_share': '_onSlidesSocialShare',
        'click .o_clipboard_button': '_onShareLinkCopy',
    },

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        var defs = [this._super.apply(this, arguments)];
        defs.push(new ShareMail(this).attachTo($('.oe_slide_js_share_email')));

        return Promise.all(defs);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {Object} ev
     */
    _onSlidesSocialShare: function (ev) {
        ev.preventDefault();
        var popUpURL = $(ev.currentTarget).attr('href');
        var popUp = window.open(popUpURL, 'Share Dialog', 'width=626,height=436');
        $(window).on('focus', function () {
            if (popUp.closed) {
                $(window).off('focus');
            }
        });
    },

    _onShareLinkCopy: function (ev) {
        ev.preventDefault();
        var $clipboardBtn = $(ev.currentTarget);
        $clipboardBtn.tooltip({title: "Copied !", trigger: "manual", placement: "bottom"});
        var self = this;
        var clipboard = new ClipboardJS('#' + $clipboardBtn[0].id, {
            target: function () {
                var share_link_el = self.$('#wslides_share_link_id_' + $clipboardBtn[0].id.split('id_')[1]);
                return share_link_el[0];
            },
            container: this.el
        });
        clipboard.on('success', function () {
            clipboard.destroy();
            $clipboardBtn.tooltip('show');
            _.delay(function () {
                $clipboardBtn.tooltip("hide");
            }, 800);
        });
        clipboard.on('error', function (e) {
            console.log(e);
            clipboard.destroy();
        })
    },
});
