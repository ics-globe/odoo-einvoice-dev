odoo.define('im_livechat.legacy.im_livechat.im_livechat', function (require) {
"use strict";

require('bus.BusService');
var concurrency = require('web.concurrency');
var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');
var Widget = require('web.Widget');

var WebsiteLivechat = require('im_livechat.legacy.im_livechat.model.WebsiteLivechat');
var WebsiteLivechatMessage = require('im_livechat.legacy.im_livechat.model.WebsiteLivechatMessage');
var WebsiteLivechatWindow = require('im_livechat.legacy.im_livechat.WebsiteLivechatWindow');

var _t = core._t;
var QWeb = core.qweb;

// Constants
var LIVECHAT_COOKIE_HISTORY = 'im_livechat_history';
var HISTORY_LIMIT = 15;

var RATING_TO_EMOJI = {
    "5": "😊",
    "3": "😐",
    "1": "😞"
};

// History tracking
var page = window.location.href.replace(/^.*\/\/[^/]+/, '');
var pageHistory = utils.get_cookie(LIVECHAT_COOKIE_HISTORY);
var urlHistory = [];
if (pageHistory) {
    urlHistory = JSON.parse(pageHistory) || [];
}
if (!_.contains(urlHistory, page)) {
    urlHistory.push(page);
    while (urlHistory.length > HISTORY_LIMIT) {
        urlHistory.shift();
    }
    utils.set_cookie(LIVECHAT_COOKIE_HISTORY, JSON.stringify(urlHistory), 60 * 60 * 24); // 1 day cookie
}

var LivechatButton = Widget.extend({
    className: 'openerp o_livechat_button d-print-none',
    custom_events: {
        'close_chat_window': '_onCloseChatWindow',
        'post_message_chat_window': '_onPostMessageChatWindow',
        'save_chat_window': '_onSaveChatWindow',
        'updated_typing_partners': '_onUpdatedTypingPartners',
        'updated_unread_counter': '_onUpdatedUnreadCounter',
    },
    events: {
        'click': '_openChat'
    },
    init: function (parent, serverURL, options) {
        console.log("Livechat entry point");
        this._super(parent);
        this.options = _.defaults(options || {}, {
            input_placeholder: _t("Ask something ..."),
            default_username: _t("Visitor"),
            button_text: _t("Chat with one of our collaborators"),
            default_message: _t("How may I help you?"),
        });

        this._history = null;
        // livechat model
        this._livechat = null;
        // livechat window
        this._chatWindow = null;
        this._messages = [];
        this._serverURL = serverURL;
    },
    async willStart() {
        var cookie = utils.get_cookie('im_livechat_session');
        if (cookie) {
            var channel = JSON.parse(cookie);
            this._history = await session.rpc('/mail/chat_history', {uuid: channel.uuid, limit: 100});
            this._history.reverse().forEach(message => { message.body = utils.Markup(message.body); });
        } else {
            const result = await session.rpc('/im_livechat/init', {channel_id: this.options.channel_id});
            if (!result.available_for_me) {
                return Promise.reject();
            }
            this._rule = result.rule;
        }
        return this._loadQWebTemplate();
    },
    start: function () {
        console.log("Livechat start function");
        this.$el.text(this.options.button_text);
        if (this._history) {
            this._history.forEach(m => this._addMessage(m));
            this._openChat();
        } else if (!config.device.isMobile && this._rule.action === 'auto_popup') {
            var autoPopupCookie = utils.get_cookie('im_livechat_auto_popup');
            if (!autoPopupCookie || JSON.parse(autoPopupCookie)) {
                this._autoPopupTimeout =
                    setTimeout(this._openChat.bind(this), this._rule.auto_popup_timer * 1000);
            }
        }
        this.call('bus_service', 'onNotification', this, this._onNotification);
        if (this.options.button_background_color) {
            this.$el.css('background-color', this.options.button_background_color);
        }
        if (this.options.button_text_color) {
            this.$el.css('color', this.options.button_text_color);
        }

        // If website_event_track installed, put the livechat banner above the PWA banner.
        var pwaBannerHeight = $('.o_pwa_install_banner').outerHeight(true);
        if (pwaBannerHeight) {
            this.$el.css('bottom', pwaBannerHeight + 'px');
        }

        return this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------


    /**
     * @private
     * @param {Object} data
     * @param {Object} [options={}]
     */
    _addMessage: function (data, options) {
        options = _.extend({}, this.options, options, {
            serverURL: this._serverURL,
        });
        var message = new WebsiteLivechatMessage(this, data, options);

        var hasAlreadyMessage = _.some(this._messages, function (msg) {
            return message.getID() === msg.getID();
        });
        if (hasAlreadyMessage) {
            return;
        }

        if (this._livechat) {
            this._livechat.addMessage(message);
        }

        if (options && options.prepend) {
            this._messages.unshift(message);
        } else {
            this._messages.push(message);
        }
    },
    /**
     * @private
     */
    _askFeedback: function () {
        this._chatWindow.$('.o_thread_composer input').prop('disabled', true);

        var feedback = new Feedback(this, this._livechat);
        this._chatWindow.replaceContentWith(feedback);

        feedback.on('send_message', this, this._sendMessage);
        feedback.on('feedback_sent', this, this._closeChat);
    },
    /**
     * @private
     */
    _closeChat: function () {
        this._chatWindow.destroy();
        utils.set_cookie('im_livechat_session', "", -1); // remove cookie
    },
    /**
     * @private
     * @param {Object} notification
     * @param {Object} notification.payload
     * @param {string} notification.type
     */
    _handleNotification: function ({ payload, type }) {
        switch (type) {
            case 'im_livechat.history_command': {
                if (payload.id !== this._livechat._id) {
                    return;
                }
                const cookie = utils.get_cookie(LIVECHAT_COOKIE_HISTORY);
                const history = cookie ? JSON.parse(cookie) : [];
                session.rpc('/im_livechat/history', {
                    pid: this._livechat.getOperatorPID()[0],
                    channel_uuid: this._livechat.getUUID(),
                    page_history: history,
                });
                return;
            }
            case 'mail.channel.partner/typing_status': {
                if (payload.channel_id !== this._livechat._id) {
                    return;
                }
                const partnerID = payload.partner_id;
                if (partnerID === this.options.current_partner_id) {
                    // ignore typing display of current partner.
                    return;
                }
                if (payload.is_typing) {
                    this._livechat.registerTyping({ partnerID });
                } else {
                    this._livechat.unregisterTyping({ partnerID });
                }
                return;
            }
            case 'mail.channel/new_message': {
                if (payload.id !== this._livechat._id) {
                    return;
                }
                const notificationData = payload.message;
                // If message from notif is already in chatter messages, stop handling
                if (this._messages.some(message => message.getID() === notificationData.id)) {
                    return;
                }
                notificationData.body = utils.Markup(notificationData.body);
                this._addMessage(notificationData);
                if (this._chatWindow.isFolded() || !this._chatWindow.isAtBottom()) {
                    this._livechat.incrementUnreadCounter();
                }
                this._renderMessages();
                return;
            }
        }
    },
    /**
     * @private
     */
    _loadQWebTemplate: function () {
        return session.rpc('/im_livechat/load_templates').then(function (templates) {
            _.each(templates, function (template) {
                QWeb.add_template(template);
            });
        });
    },
    /**
     * @private
     */
    _openChat: _.debounce(function () {
        if (this._openingChat) {
            return;
        }
        var self = this;
        var cookie = utils.get_cookie('im_livechat_session');
        var def;
        this._openingChat = true;
        clearTimeout(this._autoPopupTimeout);
        if (cookie) {
            def = Promise.resolve(JSON.parse(cookie));
        } else {
            this._messages = []; // re-initialize messages cache
            def = session.rpc('/im_livechat/get_session', {
                channel_id: this.options.channel_id,
                anonymous_name: this.options.default_username,
                previous_operator_id: this._get_previous_operator_id(),
            }, { shadow: true });
        }
        def.then(function (livechatData) {
            if (!livechatData || !livechatData.operator_pid) {
                try {
                    self.displayNotification({
                        message: _t("No available collaborator, please try again later."),
                        sticky: true,
                    });
                } catch (_err) {
                    /**
                     * Failure in displaying notification happens when
                     * notification service doesn't exist, which is the case in
                     * external lib. We don't want notifications in external
                     * lib at the moment because they use bootstrap toast and
                     * we don't want to include boostrap in external lib.
                     */
                    console.warn(_t("No available collaborator, please try again later."));
                }
            } else {
                self._livechat = new WebsiteLivechat({
                    parent: self,
                    data: livechatData
                });
                return self._openChatWindow().then(function () {
                    if (!self._history) {
                        self._sendWelcomeMessage();
                    }
                    self._renderMessages();
                    self.call('bus_service', 'addChannel', self._livechat.getUUID());
                    self.call('bus_service', 'startPolling');

                    utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(self._livechat.toData()), true), 60 * 60);
                    utils.set_cookie('im_livechat_auto_popup', JSON.stringify(false), 60 * 60);
                    if (livechatData.operator_pid[0]) {
                        // livechatData.operator_pid contains a tuple (id, name)
                        // we are only interested in the id
                        var operatorPidId = livechatData.operator_pid[0];
                        var oneWeek = 7 * 24 * 60 * 60;
                        utils.set_cookie('im_livechat_previous_operator_pid', operatorPidId, oneWeek);
                    }
                });
            }
        }).then(function () {
            self._openingChat = false;
        }).guardedCatch(function () {
            self._openingChat = false;
        });
    }, 200, true),
    /**
     * Will try to get a previous operator for this visitor.
     * If the visitor already had visitor A, it's better for his user experience
     * to get operator A again.
     *
     * The information is stored in the 'im_livechat_previous_operator_pid' cookie.
     *
     * @private
     * @return {integer} operator_id.partner_id.id if the cookie is set
     */
    _get_previous_operator_id: function () {
        var cookie = utils.get_cookie('im_livechat_previous_operator_pid');
        if (cookie) {
            return cookie;
        }

        return null;
    },
    /**
     * @private
     * @return {Promise}
     */
    _openChatWindow: function () {
        var self = this;
        var options = {
            displayStars: false,
            headerBackgroundColor: this.options.header_background_color,
            placeholder: this.options.input_placeholder || "",
            titleColor: this.options.title_color,
        };
        this._chatWindow = new WebsiteLivechatWindow(this, this._livechat, options);
        return this._chatWindow.appendTo($('body')).then(function () {
            var cssProps = { bottom: 0 };
            cssProps[_t.database.parameters.direction === 'rtl' ? 'left' : 'right'] = 0;
            self._chatWindow.$el.css(cssProps);
            self.$el.hide();
        });
    },
    /**
     * @private
     */
    _renderMessages: function () {
        var shouldScroll = !this._chatWindow.isFolded() && this._chatWindow.isAtBottom();
        this._livechat.setMessages(this._messages);
        this._chatWindow.render();
        if (shouldScroll) {
            this._chatWindow.scrollToBottom();
        }
    },
    /**
     * @private
     * @param {Object} message
     * @return {Promise}
     */
    _sendMessage: function (message) {
        var self = this;
        this._livechat._notifyMyselfTyping({ typing: false });
        return session
            .rpc('/mail/chat_post', { uuid: this._livechat.getUUID(), message_content: message.content })
            .then(function (messageId) {
                if (!messageId) {
                    try {
                        self.displayNotification({
                            message: _t("Session expired... Please refresh and try again."),
                            sticky: true,
                        });
                    } catch (_err) {
                        /**
                         * Failure in displaying notification happens when
                         * notification service doesn't exist, which is the case
                         * in external lib. We don't want notifications in
                         * external lib at the moment because they use bootstrap
                         * toast and we don't want to include boostrap in
                         * external lib.
                         */
                        console.warn(_t("Session expired... Please refresh and try again."));
                    }
                    self._closeChat();
                }
                self._chatWindow.scrollToBottom();
            });
    },
    /**
     * @private
     */
    _sendWelcomeMessage: function () {
        if (this.options.default_message) {
            this._addMessage({
                id: '_welcome',
                attachment_ids: [],
                author_id: this._livechat.getOperatorPID(),
                body: this.options.default_message,
                date: time.datetime_to_str(new Date()),
                model: "mail.channel",
                res_id: this._livechat.getID(),
            }, { prepend: true });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onCloseChatWindow: function (ev) {
        ev.stopPropagation();
        var isComposerDisabled = this._chatWindow.$('.o_thread_composer input').prop('disabled');
        var shouldAskFeedback = !isComposerDisabled && _.find(this._messages, function (message) {
            return message.getID() !== '_welcome';
        });
        if (shouldAskFeedback) {
            this._chatWindow.toggleFold(false);
            this._askFeedback();
        } else {
            this._closeChat();
        }
    },
    /**
     * @private
     * @param {Array[]} notifications
     */
    _onNotification: function (notifications) {
        var self = this;
        _.each(notifications, function (notification) {
            self._handleNotification(notification);
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data.messageData
     */
    _onPostMessageChatWindow: function (ev) {
        ev.stopPropagation();
        var self = this;
        var messageData = ev.data.messageData;
        this._sendMessage(messageData).guardedCatch(function (reason) {
            reason.event.preventDefault();
            return self._sendMessage(messageData); // try again just in case
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSaveChatWindow: function (ev) {
        ev.stopPropagation();
        utils.set_cookie('im_livechat_session', utils.unaccent(JSON.stringify(this._livechat.toData()), true), 60 * 60);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onUpdatedTypingPartners(ev) {
        ev.stopPropagation();
        this._chatWindow.renderHeader();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onUpdatedUnreadCounter: function (ev) {
        ev.stopPropagation();
        this._chatWindow.renderHeader();
    },
});

/*
 * Rating for Livechat
 *
 * This widget displays the 3 rating smileys, and a textarea to add a reason
 * (only for red smiley), and sends the user feedback to the server.
 */
var Feedback = Widget.extend({
    template: 'im_livechat.legacy.im_livechat.FeedBack',

    events: {
        'click .o_livechat_rating_choices img': '_onClickSmiley',
        'click .o_livechat_no_feedback span': '_onClickNoFeedback',
        'click .o_rating_submit_button': '_onClickSend',
        'click .o_email_chat_button': '_onEmailChat',
        'click .o_livechat_email_error .alert-link': '_onTryAgain',
    },

    /**
     * @param {?} parent
     * @param {im_livechat.legacy.im_livechat.model.WebsiteLivechat} livechat
     */
    init: function (parent, livechat) {
        this._super(parent);
        this._livechat = livechat;
        this.server_origin = session.origin;
        this.rating = undefined;
        this.dp = new concurrency.DropPrevious();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} options
     */
    _sendFeedback: function (reason) {
        var self = this;
        var args = {
            uuid: this._livechat.getUUID(),
            rate: this.rating,
            reason: reason,
        };
        this.dp.add(session.rpc('/im_livechat/feedback', args)).then(function (response) {
            var emoji = RATING_TO_EMOJI[self.rating] || "??";
            if (!reason) {
                var content = _.str.sprintf(_t("Rating: %s"), emoji);
            }
            else {
                var content = "Rating reason: \n" + reason;
            }
            self.trigger('send_message', { content: content, isFeedback: true });
        });
    },
    /**
    * @private
    */
    _showThanksMessage: function () {
        this.$('.o_livechat_rating_box').empty().append($('<div />', {
            text: _t('Thank you for your feedback'),
            class: 'text-muted'
        }));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickNoFeedback: function () {
        this.trigger('feedback_sent'); // will close the chat
    },
    /**
     * @private
     */
    _onClickSend: function () {
        this.$('.o_livechat_rating_reason').hide();
        this._showThanksMessage();
        if (_.isNumber(this.rating)) {
            this._sendFeedback(this.$('textarea').val());
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSmiley: function (ev) {
        this.rating = parseInt($(ev.currentTarget).data('value'));
        this.$('.o_livechat_rating_choices img').removeClass('selected');
        this.$('.o_livechat_rating_choices img[data-value="' + this.rating + '"]').addClass('selected');

        // only display textearea if bad smiley selected
        if (this.rating !== 5) {
            this._sendFeedback();
            this.$('.o_livechat_rating_reason').show();
        } else {
            this.$('.o_livechat_rating_reason').hide();
            this._showThanksMessage();
            this._sendFeedback();
        }
    },
    /**
    * @private
    */
    _onEmailChat: function () {
        var self = this;
        var $email = this.$('#o_email');

        if (utils.is_email($email.val())) {
            $email.removeAttr('title').removeClass('is-invalid').prop('disabled', true);
            this.$('.o_email_chat_button').prop('disabled', true);
            this._rpc({
                route: '/im_livechat/email_livechat_transcript',
                params: {
                    uuid: this._livechat.getUUID(),
                    email: $email.val(),
                }
            }).then(function () {
                self.$('.o_livechat_email').html($('<strong />', { text: _t('Conversation Sent') }));
            }).guardedCatch(function () {
                self.$('.o_livechat_email').hide();
                self.$('.o_livechat_email_error').show();
            });
        } else {
            $email.addClass('is-invalid').prop('title', _t('Invalid email address'));
        }
    },
    /**
    * @private
    */
    _onTryAgain: function () {
        this.$('#o_email').prop('disabled', false);
        this.$('.o_email_chat_button').prop('disabled', false);
        this.$('.o_livechat_email_error').hide();
        this.$('.o_livechat_email').show();
    },
});

return {
    LivechatButton: LivechatButton,
    Feedback: Feedback,
};

});

odoo.define('im_livechat.legacy.im_livechat.model.WebsiteLivechat', function (require) {
"use strict";

var AbstractThread = require('im_livechat.legacy.mail.model.AbstractThread');
var ThreadTypingMixin = require('im_livechat.legacy.mail.model.ThreadTypingMixin');

var session = require('web.session');

/**
 * Thread model that represents a livechat on the website-side. This livechat
 * is not linked to the mail service.
 */
var WebsiteLivechat = AbstractThread.extend(ThreadTypingMixin, {

    /**
     * @override
     * @private
     * @param {Object} params
     * @param {Object} params.data
     * @param {boolean} [params.data.folded] states whether the livechat is
     *   folded or not. It is considered only if this is defined and it is a
     *   boolean.
     * @param {integer} params.data.id the ID of this livechat.
     * @param {integer} [params.data.message_unread_counter] the unread counter
     *   of this livechat.
     * @param {Array} params.data.operator_pid
     * @param {string} params.data.name the name of this livechat.
     * @param {string} [params.data.state] if 'folded', the livechat is folded.
     *   This is ignored if `folded` is provided and is a boolean value.
     * @param {string} params.data.uuid the UUID of this livechat.
     * @param {im_livechat.legacy.im_livechat.im_livechat:LivechatButton} params.parent
     */
    init: function (params) {
        this._super.apply(this, arguments);
        ThreadTypingMixin.init.call(this, arguments);

        this._members = [];
        this._operatorPID = params.data.operator_pid;
        this._uuid = params.data.uuid;

        if (params.data.message_unread_counter !== undefined) {
            this._unreadCounter = params.data.message_unread_counter;
        }

        if (_.isBoolean(params.data.folded)) {
            this._folded = params.data.folded;
        } else {
            this._folded = params.data.state === 'folded';
        }

        // Necessary for thread typing mixin to display is typing notification
        // bar text (at least, for the operator in the members).
        this._members.push({
            id: this._operatorPID[0],
            name: this._operatorPID[1]
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {im_livechat.legacy.im_livechat.model.WebsiteLivechatMessage[]}
     */
    getMessages: function () {
        return this._messages;
    },
    /**
     * @returns {Array}
     */
    getOperatorPID: function () {
        return this._operatorPID;
    },
    /**
     * @returns {string}
     */
    getUUID: function () {
        return this._uuid;
    },
    /**
     * Increments the unread counter of this livechat by 1 unit.
     *
     * Note: this public method makes sense because the management of messages
     * for website livechat is external. This method should be dropped when
     * this class handles messages by itself.
     */
    incrementUnreadCounter: function () {
        this._incrementUnreadCounter();
    },
    /**
     * AKU: hack for the moment
     *
     * @param {im_livechat.legacy.im_livechat.model.WebsiteLivechatMessage[]} messages
     */
    setMessages: function (messages) {
        this._messages = messages;
    },
    /**
     * @returns {Object}
     */
    toData: function () {
        return {
            folded: this.isFolded(),
            id: this.getID(),
            message_unread_counter: this.getUnreadCounter(),
            operator_pid: this.getOperatorPID(),
            name: this.getName(),
            uuid: this.getUUID(),
        };
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {Object} params
     * @param {boolean} params.isWebsiteUser
     * @returns {boolean}
     */
    _isTypingMyselfInfo: function (params) {
        return params.isWebsiteUser;
    },
    /**
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {Object} params
     * @param {boolean} params.typing
     * @returns {Promise}
     */
    _notifyMyselfTyping: function (params) {
        console.log("Notifying Myself Typing", params.typing)
        return session.rpc('/im_livechat/notify_typing', {
            uuid: this.getUUID(),
            is_typing: params.typing,
        }, { shadow: true });
    },
    /**
     * Warn views that the list of users that are currently typing on this
     * livechat has been updated.
     *
     * @override {mail.model.ThreadTypingMixin}
     * @private
     */
    _warnUpdatedTypingPartners: function () {
        this.trigger_up('updated_typing_partners');
    },
    /**
     * Warn that the unread counter has been updated on this livechat
     *
     * @override
     * @private
     */
    _warnUpdatedUnreadCounter: function () {
        this.trigger_up('updated_unread_counter');
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * Override so that it only unregister typing operators.
     *
     * Note that in the frontend, there is no way to identify a message that is
     * from the current user, because there is no partner ID in the session and
     * a message with an author sets the partner ID of the author.
     *
     * @override {mail.model.ThreadTypingMixin}
     * @private
     * @param {mail.model.AbstractMessage} message
     */
    _onTypingMessageAdded: function (message) {
        var operatorID = this.getOperatorPID()[0];
        if (message.hasAuthor() && message.getAuthorID() === operatorID) {
            this.unregisterTyping({ partnerID: operatorID });
        }
    },
});

return WebsiteLivechat;

});


console.log("a")
const { Component, mount, xml } = owl;
console.log("App:", this.App);
class Livechat extends Component {
  static template = xml`<div>todo app</div>`;
  init(){
    console.log("ttt");
  }
  setup(){
    console.log("OWL ADD-ON SETUP");
  }
}
