odoo.define('im_livechat.legacy.mail.widget.Thread', function (require) {
"use strict";

var DocumentViewer = require('im_livechat.legacy.mail.DocumentViewer');
var mailUtils = require('@mail/js/utils');

var core = require('web.core');
var time = require('web.time');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _lt = core._lt;

var ORDER = {
    ASC: 1, // visually, ascending order of message IDs (from top to bottom)
    DESC: -1, // visually, descending order of message IDs (from top to bottom)
};

var READ_MORE = _lt("read more");
var READ_LESS = _lt("read less");

/**
 * This is a generic widget to render a thread.
 * Any thread that extends mail.model.AbstractThread can be used with this
 * widget.
 */
var ThreadWidget = Widget.extend({
    className: 'o_mail_thread',

    events: {
        'click a': '_onClickRedirect',
        'click img': '_onClickRedirect',
        'click strong': '_onClickRedirect',
        'click .o_thread_show_more': '_onClickShowMore',
        'click .o_attachment_download': '_onAttachmentDownload',
        'click .o_attachment_view': '_onAttachmentView',
        'click .o_attachment_delete_cross': '_onDeleteAttachment',
        'click .o_thread_message_needaction': '_onClickMessageNeedaction',
        'click .o_thread_message_star': '_onClickMessageStar',
        'click .o_thread_message_reply': '_onClickMessageReply',
        'click .oe_mail_expand': '_onClickMailExpand',
        'click .o_thread_message': '_onClickMessage',
        'click': '_onClick',
        'click .o_thread_message_notification_error': '_onClickMessageNotificationError',
        'click .o_thread_message_moderation': '_onClickMessageModeration',
        'change .moderation_checkbox': '_onChangeModerationCheckbox',
    },

    /**
     * @override
     * @param {widget} parent
     * @param {Object} options
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.attachments = [];
        // options when the thread is enabled (e.g. can send message,
        // interact on messages, etc.)
        this._enabledOptions = _.defaults(options || {}, {
            displayOrder: ORDER.ASC,
            displayMarkAsRead: true,
            displayModerationCommands: false,
            displayStars: true,
            displayDocumentLinks: true,
            displayAvatars: true,
            squashCloseMessages: true,
            displayNotificationIcons: true,
            displayReplyIcons: false,
            loadMoreOnScroll: false,
            hasMessageAttachmentDeletable: false,
        });
        // options when the thread is disabled
        this._disabledOptions = {
            displayOrder: this._enabledOptions.displayOrder,
            displayMarkAsRead: false,
            displayModerationCommands: false,
            displayStars: false,
            displayDocumentLinks: false,
            displayAvatars: this._enabledOptions.displayAvatars,
            squashCloseMessages: false,
            displayNotificationIcons: false,
            displayReplyIcons: false,
            loadMoreOnScroll: this._enabledOptions.loadMoreOnScroll,
            hasMessageAttachmentDeletable: false,
        };
        this._selectedMessageID = null;
        this._currentThreadID = null;
        this._messageMailPopover = null;
        this._messageSeenPopover = null;
        // used to track popover IDs to destroy on re-rendering of popovers
        this._openedSeenPopoverIDs = [];
    },
    /**
     * The message mail popover may still be shown at this moment. If we do not
     * remove it, it stays visible on the page until a page reload.
     *
     * @override
     */
    destroy: function () {
        clearInterval(this._updateTimestampsInterval);
        if (this._messageMailPopover) {
            this._messageMailPopover.popover('hide');
        }
        if (this._messageSeenPopover) {
            this._messageSeenPopover.popover('hide');
        }
        this._destroyOpenSeenPopoverIDs();
        this._super();
    },
    /**
     * @param {im_livechat.legacy.mail.model.AbstractThread} thread the thread to render.
     * @param {Object} [options]
     * @param {integer} [options.displayOrder=ORDER.ASC] order of displaying
     *    messages in the thread:
     *      - ORDER.ASC: last message is at the bottom of the thread
     *      - ORDER.DESC: last message is at the top of the thread
     * @param {boolean} [options.displayLoadMore]
     * @param {Array} [options.domain=[]] the domain for the messages in the
     *    thread.
     * @param {boolean} [options.isCreateMode]
     * @param {boolean} [options.scrollToBottom=false]
     * @param {boolean} [options.squashCloseMessages]
     */
    render: function (thread, options) {
        var self = this;

        var shouldScrollToBottomAfterRendering = false;
        if (this._currentThreadID === thread.getID() && this.isAtBottom()) {
            shouldScrollToBottomAfterRendering = true;
        }
        this._currentThreadID = thread.getID();

        // copy so that reverse do not alter order in the thread object
        var messages = _.clone(thread.getMessages({ domain: options.domain || [] }));

        var modeOptions = options.isCreateMode ? this._disabledOptions :
                                                    this._enabledOptions;

        // attachments ordered by messages order (increasing ID)
        this.attachments = _.uniq(_.flatten(_.map(messages, function (message) {
            return message.getAttachments();
        })));

        options = _.extend({}, modeOptions, options, {
            selectedMessageID: this._selectedMessageID,
        });

        // dict where key is message ID, and value is whether it should display
        // the author of message or not visually
        var displayAuthorMessages = {};

        // Hide avatar and info of a message if that message and the previous
        // one are both comments wrote by the same author at the same minute
        // and in the same document (users can now post message in documents
        // directly from a channel that follows it)
        var prevMessage;
        _.each(messages, function (message) {
            if (
                // is first message of thread
                !prevMessage ||
                // more than 1 min. elasped
                (Math.abs(message.getDate().diff(prevMessage.getDate())) > 60000) ||
                prevMessage.getType() !== 'comment' ||
                message.getType() !== 'comment' ||
                // from a different author
                (prevMessage.getAuthorID() !== message.getAuthorID()) ||
                (
                    // messages are linked to a document thread
                    (
                        prevMessage.isLinkedToDocumentThread() &&
                        message.isLinkedToDocumentThread()
                    ) &&
                    (
                        // are from different documents
                        prevMessage.getDocumentModel() !== message.getDocumentModel() ||
                        prevMessage.getDocumentID() !== message.getDocumentID()
                    )
                )
            ) {
                displayAuthorMessages[message.getID()] = true;
            } else {
                displayAuthorMessages[message.getID()] = !options.squashCloseMessages;
            }
            prevMessage = message;
        });

        if (modeOptions.displayOrder === ORDER.DESC) {
            messages.reverse();
        }

        this.$el.html(QWeb.render('im_livechat.legacy.mail.widget.Thread', {
            thread: thread,
            displayAuthorMessages: displayAuthorMessages,
            options: options,
            ORDER: ORDER,
            dateFormat: time.getLangDatetimeFormat(),
        }));

        _.each(messages, function (message) {
            var $message = self.$('.o_thread_message[data-message-id="' + message.getID() + '"]');
            $message.find('.o_mail_timestamp').data('date', message.getDate());

            self._insertReadMore($message);
        });

        if (shouldScrollToBottomAfterRendering) {
            this.scrollToBottom();
        }

        if (!this._updateTimestampsInterval) {
            this.updateTimestampsInterval = setInterval(function () {
                self._updateTimestamps();
            }, 1000 * 60);
        }

        this._renderMessageNotificationPopover(messages);
        if (thread.hasSeenFeature()) {
            this._renderMessageSeenPopover(thread, messages);
        }
    },

    /**
     * Render thread widget when loading, i.e. when messaging is not yet ready.
     * @see /mail/init_messaging
     */
    renderLoading: function () {
        this.$el.html(QWeb.render('im_livechat.legacy.mail.widget.ThreadLoading'));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    getScrolltop: function () {
        return this.$el.scrollTop();
    },
    /**
     * State whether the bottom of the thread is visible or not,
     * with a tolerance of 5 pixels
     *
     * @return {boolean}
     */
    isAtBottom: function () {
        var fullHeight = this.el.scrollHeight;
        var topHiddenHeight = this.$el.scrollTop();
        var visibleHeight = this.$el.outerHeight();
        var bottomHiddenHeight = fullHeight - topHiddenHeight - visibleHeight;
        return bottomHiddenHeight < 5;
    },
    /**
     * Removes a message and re-renders the thread
     *
     * @param {integer} [messageID] the id of the removed message
     * @param {mail.model.AbstractThread} thread the thread which contains
     *   updated list of messages (so it does not contain any message with ID
     *   `messageID`).
     * @param {Object} [options] options for the thread rendering
     */
    removeMessageAndRender: function (messageID, thread, options) {
        var self = this;
        this._currentThreadID = thread.getID();
        return new Promise(function (resolve, reject) {
            self.$('.o_thread_message[data-message-id="' + messageID + '"]')
            .fadeOut({
                done: function () {
                    if (self._currentThreadID === thread.getID()) {
                        self.render(thread, options);
                    }
                    resolve();
                },
                duration: 200,
            });
        });
    },
    /**
     * Scroll to the bottom of the thread
     */
    scrollToBottom: function () {
        this.$el.scrollTop(this.el.scrollHeight);
    },
    /**
     * Scrolls the thread to a given message
     *
     * @param {integer} options.msgID the ID of the message to scroll to
     * @param {integer} [options.duration]
     * @param {boolean} [options.onlyIfNecessary]
     */
    scrollToMessage: function (options) {
        var $target = this.$('.o_thread_message[data-message-id="' + options.messageID + '"]');
        if (options.onlyIfNecessary) {
            var delta = $target.parent().height() - $target.height();
            var offset = delta < 0 ?
                            0 :
                            delta - ($target.offset().top - $target.offsetParent().offset().top);
            offset = - Math.min(offset, 0);
            this.$el.scrollTo("+=" + offset + "px", options.duration);
        } else if ($target.length) {
            this.$el.scrollTo($target);
        }
    },
    /**
     * Scroll to the specific position in pixel
     *
     * If no position is provided, scroll to the bottom of the thread
     *
     * @param {integer} [position] distance from top to position in pixels.
     *    If not provided, scroll to the bottom.
     */
    scrollToPosition: function (position) {
        if (position) {
            this.$el.scrollTop(position);
        } else {
            this.scrollToBottom();
        }
    },
    /**
     * Toggle all the moderation checkboxes in the thread
     *
     * @param {boolean} checked if true, check the boxes,
     *      otherwise uncheck them.
     */
    toggleModerationCheckboxes: function (checked) {
        this.$('.moderation_checkbox').prop('checked', checked);
    },
    /**
     * Unselect the selected message
     */
    unselectMessage: function () {
        this.$('.o_thread_message').removeClass('o_thread_selected_message');
        this._selectedMessageID = null;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _destroyOpenSeenPopoverIDs: function () {
        _.each(this._openedSeenPopoverIDs, function (popoverID) {
            $('#' + popoverID).remove();
        });
        this._openedSeenPopoverIDs = [];
    },
    /**
     * Modifies $element to add the 'read more/read less' functionality
     * All element nodes with 'data-o-mail-quote' attribute are concerned.
     * All text nodes after a ``#stopSpelling`` element are concerned.
     * Those text nodes need to be wrapped in a span (toggle functionality).
     * All consecutive elements are joined in one 'read more/read less'.
     *
     * @private
     * @param {jQuery} $element
     */
    _insertReadMore: function ($element) {
        var self = this;

        var groups = [];
        var readMoreNodes;

        // nodeType 1: element_node
        // nodeType 3: text_node
        var $children = $element.contents()
            .filter(function () {
                return this.nodeType === 1 ||
                        this.nodeType === 3 &&
                        this.nodeValue.trim();
            });

        _.each($children, function (child) {
            var $child = $(child);

            // Hide Text nodes if "stopSpelling"
            if (
                child.nodeType === 3 &&
                $child.prevAll('[id*="stopSpelling"]').length > 0
            ) {
                // Convert Text nodes to Element nodes
                $child = $('<span>', {
                    text: child.textContent,
                    'data-o-mail-quote': '1',
                });
                child.parentNode.replaceChild($child[0], child);
            }

            // Create array for each 'read more' with nodes to toggle
            if (
                $child.attr('data-o-mail-quote') ||
                (
                    $child.get(0).nodeName === 'BR' &&
                    $child.prev('[data-o-mail-quote="1"]').length > 0
                )
            ) {
                if (!readMoreNodes) {
                    readMoreNodes = [];
                    groups.push(readMoreNodes);
                }
                $child.hide();
                readMoreNodes.push($child);
            } else {
                readMoreNodes = undefined;
                self._insertReadMore($child);
            }
        });

        _.each(groups, function (group) {
            // Insert link just before the first node
            var $readMore = $('<a>', {
                class: 'o_mail_read_more',
                href: '#',
                text: READ_MORE,
            }).insertBefore(group[0]);

            // Toggle All next nodes
            var isReadMore = true;
            $readMore.click(function (e) {
                e.preventDefault();
                isReadMore = !isReadMore;
                _.each(group, function ($child) {
                    $child.hide();
                    $child.toggle(!isReadMore);
                });
                $readMore.text(isReadMore ? READ_MORE : READ_LESS);
            });
        });
    },
    /**
    * @private
    * @param {MouseEvent} ev
    */
    _onDeleteAttachment: function (ev) {
        ev.stopPropagation();
        var $target = $(ev.currentTarget);
        this.trigger_up('delete_attachment', {
            attachmentId: $target.data('id'),
            attachmentName: $target.data('name')
        });
        },
    /**
     * @private
     * @param {Object} options
     * @param {integer} [options.channelID]
     * @param {string} options.model
     * @param {integer} options.id
     */
    _redirect: _.debounce(function (options) {
        if ('channelID' in options) {
            this.trigger('redirect_to_channel', options.channelID);
        } else {
            this.trigger('redirect', options.model, options.id);
        }
    }, 500, true),
    /**
     * Render the popover when mouse-hovering on the notification icon of a
     * message in the thread.
     * There is at most one such popover at any given time.
     *
     * @private
     * @param {im_livechat.legacy.mail.model.AbstractMessage[]} messages list of messages in the
     *   rendered thread, for which popover on mouseover interaction is
     *   permitted.
     */
    _renderMessageNotificationPopover(messages) {
        if (this._messageMailPopover) {
            this._messageMailPopover.popover('hide');
        }
        if (!this.$('.o_thread_tooltip').length) {
            return;
        }
        this._messageMailPopover = this.$('.o_thread_tooltip').popover({
            html: true,
            boundary: 'viewport',
            placement: 'auto',
            trigger: 'hover',
            offset: '0, 1',
            content: function () {
                var messageID = $(this).data('message-id');
                var message = _.find(messages, function (message) {
                    return message.getID() === messageID;
                });
                return QWeb.render('im_livechat.legacy.mail.widget.Thread.Message.MailTooltip', {
                    notifications: message.getNotifications(),
                });
            },
        });
    },
    /**
     * Render the popover when mouse hovering on the seen icon of a message
     * in the thread. Only seen icons in non-squashed message have popover,
     * because squashed messages hides this icon on message mouseover.
     *
     * @private
     * @param {im_livechat.legacy.mail.model.AbstractThread} thread with thread seen mixin,
     *   @see {im_livechat.legacy.mail.model.ThreadSeenMixin}
     * @param {im_livechat.legacy.mail.model.Message[]} messages list of messages in the
     *   rendered thread.
     */
    _renderMessageSeenPopover: function (thread, messages) {
        var self = this;
        this._destroyOpenSeenPopoverIDs();
        if (this._messageSeenPopover) {
            this._messageSeenPopover.popover('hide');
        }
        if (!this.$('.o_thread_message_core .o_mail_thread_message_seen_icon').length) {
            return;
        }
        this._messageSeenPopover = this.$('.o_thread_message_core .o_mail_thread_message_seen_icon').popover({
            html: true,
            boundary: 'viewport',
            placement: 'auto',
            trigger: 'hover',
            offset: '0, 1',
            content: function () {
                var $this = $(this);
                self._openedSeenPopoverIDs.push($this.attr('aria-describedby'));
                var messageID = $this.data('message-id');
                var message = _.find(messages, function (message) {
                    return message.getID() === messageID;
                });
                return QWeb.render('im_livechat.legacy.mail.widget.Thread.Message.SeenIconPopoverContent', {
                    thread: thread,
                    message: message,
                });
            },
        });
    },
    /**
     * @private
     */
    _updateTimestamps: function () {
        var isAtBottom = this.isAtBottom();
        this.$('.o_mail_timestamp').each(function () {
            var date = $(this).data('date');
            $(this).html(mailUtils.timeFromNow(date));
        });
        if (isAtBottom && !this.isAtBottom()) {
            this.scrollToBottom();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAttachmentDownload: function (event) {
        event.stopPropagation();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAttachmentView: function (event) {
        event.stopPropagation();
        var activeAttachmentID = $(event.currentTarget).data('id');
        if (activeAttachmentID) {
            var attachmentViewer = new DocumentViewer(this, this.attachments, activeAttachmentID);
            attachmentViewer.appendTo($('body'));
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onChangeModerationCheckbox: function (ev) {
        this.trigger_up('update_moderation_buttons');
    },
    /**
     * @private
     */
    _onClick: function () {
        if (this._selectedMessageID) {
            this.unselectMessage();
            this.trigger('unselect_message');
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMailExpand: function (ev) {
        ev.preventDefault();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessage: function (ev) {
        $(ev.currentTarget).toggleClass('o_thread_selected_message');
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageNeedaction: function (ev) {
        var messageID = $(ev.currentTarget).data('message-id');
        this.trigger('mark_as_read', messageID);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageNotificationError(ev) {
        const messageID = $(ev.currentTarget).data('message-id');
        this.do_action('mail.mail_resend_message_action', {
            additional_context: {
                mail_message_to_resend: messageID,
            }
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageReply: function (ev) {
        this._selectedMessageID = $(ev.currentTarget).data('message-id');
        this.$('.o_thread_message').removeClass('o_thread_selected_message');
        this.$('.o_thread_message[data-message-id="' + this._selectedMessageID + '"]')
            .addClass('o_thread_selected_message');
        this.trigger('select_message', this._selectedMessageID);
        ev.stopPropagation();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageStar: function (ev) {
        var messageID = $(ev.currentTarget).data('message-id');
        this.trigger('toggle_star_status', messageID);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageModeration: function (ev) {
        var $button = $(ev.currentTarget);
        var messageID = $button.data('message-id');
        var decision = $button.data('decision');
        this.trigger_up('message_moderation', {
            messageID: messageID,
            decision: decision,
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRedirect: function (ev) {
        // ignore inherited branding
        if ($(ev.target).data('oe-field') !== undefined) {
            return;
        }
        var id = $(ev.target).data('oe-id');
        if (id) {
            ev.preventDefault();
            var model = $(ev.target).data('oe-model');
            var options;
            if (model && (model !== 'mail.channel')) {
                options = {
                    model: model,
                    id: id
                };
            } else {
                options = { channelID: id };
            }
            this._redirect(options);
        }
    },
    /**
     * @private
     */
    _onClickShowMore: function () {
        this.trigger('load_more_messages');
    },
});

ThreadWidget.ORDER = ORDER;

return ThreadWidget;

});

odoo.define('im_livechat.legacy.mail.model.ThreadTypingMixin', function (require) {
"use strict";

var CCThrottleFunction = require('im_livechat.legacy.mail.model.CCThrottleFunction');
var Timer = require('im_livechat.legacy.mail.model.Timer');
var Timers = require('im_livechat.legacy.mail.model.Timers');

var core = require('web.core');

var _t = core._t;

/**
 * Mixin for enabling the "is typing..." notification on a type of thread.
 */
var ThreadTypingMixin = {
    // Default partner infos
    _DEFAULT_TYPING_PARTNER_ID: '_default',
    _DEFAULT_TYPING_PARTNER_NAME: 'Someone',

    /**
     * Initialize the internal data for typing feature on threads.
     *
     * Also listens on some internal events of the thread:
     *
     * - 'message_added': when a message is added, remove the author in the
     *     typing partners.
     * - 'message_posted': when a message is posted, let the user have the
     *     possibility to immediately notify if he types something right away,
     *     instead of waiting for a throttle behaviour.
     */
    init: function () {
        // Store the last "myself typing" status that has been sent to the
        // server. This is useful in order to not notify the same typing
        // status multiple times.
        this._lastNotifiedMyselfTyping = false;

        // Timer of current user that is typing a very long text. When the
        // receivers do not receive any typing notification for a long time,
        // they assume that the related partner is no longer typing
        // something (e.g. they have closed the browser tab).
        // This is a timer to let others know that we are still typing
        // something, so that they do not assume we stopped typing
        // something.
        this._myselfLongTypingTimer = new Timer({
            duration: 50 * 1000,
            onTimeout: this._onMyselfLongTypingTimeout.bind(this),
        });

        // Timer of current user that was currently typing something, but
        // there is no change on the input for several time. This is used
        // in order to automatically notify other users that we have stopped
        // typing something, due to making no changes on the composer for
        // some time.
        this._myselfTypingInactivityTimer = new Timer({
            duration: 5 * 1000,
            onTimeout: this._onMyselfTypingInactivityTimeout.bind(this),
        });

        // Timers of users currently typing in the thread. This is useful
        // in order to automatically unregister typing users when we do not
        // receive any typing notification after a long time. Timers are
        // internally indexed by partnerID. The current user is ignored in
        // this list of timers.
        this._othersTypingTimers = new Timers({
            duration: 60 * 1000,
            onTimeout: this._onOthersTypingTimeout.bind(this),
        });

        // Clearable and cancellable throttled version of the
        // `doNotifyMyselfTyping` method. (basically `notifyMyselfTyping`
        // with slight pre- and post-processing)
        // @see {mail.model.ResetableThrottleFunction}
        // This is useful when the user posts a message and types something
        // else: he must notify immediately that he is typing something,
        // instead of waiting for the throttle internal timer.
        this._throttleNotifyMyselfTyping = CCThrottleFunction({
            duration: 2.5 * 1000,
            func: this._onNotifyMyselfTyping.bind(this),
        });

        // This is used to track the order of registered partners typing
        // something, in order to display the oldest typing partners.
        this._typingPartnerIDs = [];

        this.on('message_added', this, this._onTypingMessageAdded);
        this.on('message_posted', this, this._onTypingMessagePosted);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the text to display when some partners are typing something on the
     * thread:
     *
     * - single typing partner:
     *
     *   A is typing...
     *
     * - two typing partners:
     *
     *   A and B are typing...
     *
     * - three or more typing partners:
     *
     *   A, B and more are typing...
     *
     * The choice of the members name for display is not random: it displays
     * the user that have been typing for the longest time. Also, this function
     * is hard-coded to display at most 2 partners. This limitation comes from
     * how translation works in Odoo, for which unevaluated string cannot be
     * translated.
     *
     * @returns {string} list of members that are typing something on the thread
     *   (excluding the current user).
     */
    getTypingMembersToText: function () {
        var typingPartnerIDs = this._typingPartnerIDs;
        var typingMembers = _.filter(this._members, function (member) {
            return _.contains(typingPartnerIDs, member.id);
        });
        var sortedTypingMembers = _.sortBy(typingMembers, function (member) {
            return _.indexOf(typingPartnerIDs, member.id);
        });
        var displayableTypingMembers = sortedTypingMembers.slice(0, 3);

        if (displayableTypingMembers.length === 0) {
            return '';
        } else if (displayableTypingMembers.length === 1) {
            return _.str.sprintf(_t("%s is typing..."), displayableTypingMembers[0].name);
        } else if (displayableTypingMembers.length === 2) {
            return _.str.sprintf(_t("%s and %s are typing..."),
                                    displayableTypingMembers[0].name,
                                    displayableTypingMembers[1].name);
        } else {
            return _.str.sprintf(_t("%s, %s and more are typing..."),
                                    displayableTypingMembers[0].name,
                                    displayableTypingMembers[1].name);
        }
    },
    /**
     * Threads with this mixin have the typing notification feature
     *
     * @returns {boolean}
     */
    hasTypingNotification: function () {
        return true;
    },
    /**
     * Tells if someone other than current user is typing something on this
     * thread.
     *
     * @returns {boolean}
     */
    isSomeoneTyping: function () {
        return !(_.isEmpty(this._typingPartnerIDs));
    },
    /**
     * Register someone that is currently typing something in this thread.
     * If this is the current user that is typing something, don't do anything
     * (we do not have to display anything)
     *
     * This method is ignored if we try to register the current user.
     *
     * @param {Object} params
     * @param {integer} params.partnerID ID of the partner linked to the user
     *   currently typing something on the thread.
     */
    registerTyping: function (params) {
        if (this._isTypingMyselfInfo(params)) {
            return;
        }
        var partnerID = params.partnerID;
        this._othersTypingTimers.registerTimer({
            timeoutCallbackArguments: [partnerID],
            timerID: partnerID,
        });
        if (_.contains(this._typingPartnerIDs, partnerID)) {
            return;
        }
        this._typingPartnerIDs.push(partnerID);
        this._warnUpdatedTypingPartners();
    },
    /**
     * This method must be called when the user starts or stops typing something
     * in the composer of the thread.
     *
     * @param {Object} params
     * @param {boolean} params.typing tell whether the current is typing or not.
     */
    setMyselfTyping: function (params) {
        var typing = params.typing;
        if (this._lastNotifiedMyselfTyping === typing) {
            this._throttleNotifyMyselfTyping.cancel();
        } else {
            this._throttleNotifyMyselfTyping(params);
        }

        if (typing) {
            this._myselfTypingInactivityTimer.reset();
        } else {
            this._myselfTypingInactivityTimer.clear();
        }
    },
    /**
     * Unregister someone from currently typing something in this thread.
     *
     * @param {Object} params
     * @param {integer} params.partnerID ID of the partner related to the user
     *   that is currently typing something
     */
    unregisterTyping: function (params) {
        var partnerID = params.partnerID;
        this._othersTypingTimers.unregisterTimer({ timerID: partnerID });
        if (!_.contains(this._typingPartnerIDs, partnerID)) {
            return;
        }
        this._typingPartnerIDs = _.reject(this._typingPartnerIDs, function (id) {
            return id === partnerID;
        });
        this._warnUpdatedTypingPartners();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Tells whether the provided information on a partner is related to the
     * current user or not.
     *
     * @abstract
     * @private
     * @param {Object} params
     * @param {integer} params.partner ID of partner to check
     */
    _isTypingMyselfInfo: function (params) {
        return false;
    },
    /**
     * Notify to the server that the current user either starts or stops typing
     * something.
     *
     * @abstract
     * @private
     * @param {Object} params
     * @param {boolean} params.typing whether we are typing something or not
     * @returns {Promise} resolved if the server is notified, rejected
     *   otherwise
     */
    _notifyMyselfTyping: function (params) {
        return Promise.resolve();
    },
    /**
     * Warn views that the list of users that are currently typing on this
     * thread has been updated.
     *
     * @abstract
     * @private
     */
    _warnUpdatedTypingPartners: function () {},

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when current user is typing something for a long time. In order
     * to not let other users assume that we are no longer typing something, we
     * must notify again that we are typing something.
     *
     * @private
     */
    _onMyselfLongTypingTimeout: function () {
        this._throttleNotifyMyselfTyping.clear();
        this._throttleNotifyMyselfTyping({ typing: true });
    },
    /**
     * Called when current user has something typed in the composer, but is
     * inactive for some time. In this case, he automatically notifies that he
     * is no longer typing something
     *
     * @private
     */
    _onMyselfTypingInactivityTimeout: function () {
        this._throttleNotifyMyselfTyping.clear();
        this._throttleNotifyMyselfTyping({ typing: false });
    },
    /**
     * Called by throttled version of notify myself typing
     *
     * Notify to the server that the current user either starts or stops typing
     * something. Remember last notified stuff from the server, and update
     * related typing timers.
     *
     * @private
     * @param {Object} params
     * @param {boolean} params.typing whether we are typing something or not.
     */
    _onNotifyMyselfTyping: function (params) {
        var typing = params.typing;
        this._lastNotifiedMyselfTyping = typing;
        this._notifyMyselfTyping(params);
        if (typing) {
            this._myselfLongTypingTimer.reset();
        } else {
            this._myselfLongTypingTimer.clear();
        }
    },
    /**
     * Called when current user do not receive a typing notification of someone
     * else typing for a long time. In this case, we assume that this person is
     * no longer typing something.
     *
     * @private
     * @param {integer} partnerID partnerID of the person we assume he is no
     *   longer typing something.
     */
    _onOthersTypingTimeout: function (partnerID) {
        this.unregisterTyping({ partnerID: partnerID });
    },
    /**
     * Called when a new message is added to the thread
     * On receiving a message from a typing partner, unregister this partner
     * from typing partners (otherwise, it will still display it until timeout).
     *
     * @private
     * @param {mail.model.AbstractMessage} message
     */
    _onTypingMessageAdded: function (message) {
        var partnerID = message.hasAuthor() ?
                        message.getAuthorID() :
                        this._DEFAULT_TYPING_PARTNER_ID;
        this.unregisterTyping({ partnerID: partnerID });
    },
    /**
     * Called when current user has posted a message on this thread.
     *
     * The current user receives the possibility to immediately notify the
     * other users if he is typing something else.
     *
     * Refresh the context for the current user to notify that he starts or
     * stops typing something. In other words, when this function is called and
     * then the current user types something, it immediately notifies the
     * server as if it is the first time he is typing something.
     *
     * @private
     */
    _onTypingMessagePosted: function () {
        this._lastNotifiedMyselfTyping = false;
        this._throttleNotifyMyselfTyping.clear();
        this._myselfLongTypingTimer.clear();
        this._myselfTypingInactivityTimer.clear();
    },
};

return ThreadTypingMixin;

});

odoo.define('im_livechat.legacy.mail.AbstractThreadWindow', function (require) {
"use strict";

var ThreadWidget = require('im_livechat.legacy.mail.widget.Thread');

var config = require('web.config');
var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

/**
 * This is an abstract widget for rendering thread windows.
 * AbstractThreadWindow is kept for legacy reasons.
 */
var AbstractThreadWindow = Widget.extend({
    template: 'im_livechat.legacy.mail.AbstractThreadWindow',
    custom_events: {
        document_viewer_closed: '_onDocumentViewerClose',
    },
    events: {
        'click .o_thread_window_close': '_onClickClose',
        'click .o_thread_window_title': '_onClickFold',
        'click .o_composer_text_field': '_onComposerClick',
        'click .o_mail_thread': '_onThreadWindowClicked',
        'keydown .o_composer_text_field': '_onKeydown',
        'keypress .o_composer_text_field': '_onKeypress',
    },
    FOLD_ANIMATION_DURATION: 200, // duration in ms for (un)fold transition
    HEIGHT_OPEN: '400px', // height in px of thread window when open
    HEIGHT_FOLDED: '34px', // height, in px, of thread window when folded
    /**
     * Children of this class must make use of `thread`, which is an object that
     * represent the thread that is linked to this thread window.
     *
     * If no thread is provided, this will represent the "blank" thread window.
     *
     * @abstract
     * @param {Widget} parent
     * @param {im_livechat.legacy.mail.model.AbstractThread} [thread=null] the thread that this
     *   thread window is linked to. If not set, it is the "blank" thread
     *   window.
     * @param {Object} [options={}]
     * @param {im_livechat.legacy.mail.model.AbstractThread} [options.thread]
     */
    init: function (parent, thread, options) {
        this._super(parent);

        this.options = _.defaults(options || {}, {
            autofocus: true,
            displayStars: true,
            displayReplyIcons: false,
            displayNotificationIcons: false,
            placeholder: _t("Say something"),
        });

        this._hidden = false;
        this._thread = thread || null;

        this._debouncedOnScroll = _.debounce(this._onScroll.bind(this), 100);

        if (!this.hasThread()) {
            // internal fold state of thread window without any thread
            this._folded = false;
        }
    },
    start: function () {
        var self = this;
        this.$input = this.$('.o_composer_text_field');
        this.$header = this.$('.o_thread_window_header');
        var options = {
            displayMarkAsRead: false,
            displayStars: this.options.displayStars,
        };
        if (this._thread && this._thread._type === 'document_thread') {
            options.displayDocumentLinks = false;
        }
        this._threadWidget = new ThreadWidget(this, options);

        // animate the (un)folding of thread windows
        this.$el.css({ transition: 'height ' + this.FOLD_ANIMATION_DURATION + 'ms linear' });
        if (this.isFolded()) {
            this.$el.css('height', this.HEIGHT_FOLDED);
        } else if (this.options.autofocus) {
            this._focusInput();
        }
        if (!config.device.isMobile) {
            var margin_dir = _t.database.parameters.direction === "rtl" ? "margin-left" : "margin-right";
            this.$el.css(margin_dir, $.position.scrollbarWidth());
        }
        var def = this._threadWidget.replace(this.$('.o_thread_window_content')).then(function () {
            self._threadWidget.$el.on('scroll', self, self._debouncedOnScroll);
        });
        return Promise.all([this._super(), def]);
    },
    /**
     * @override
     */
    do_hide: function () {
        this._hidden = true;
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    do_show: function () {
        this._hidden = false;
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    do_toggle: function (display) {
        this._hidden = _.isBoolean(display) ? !display : !this._hidden;
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Close this window
     *
     * @abstract
     */
    close: function () {},
    /**
     * Get the ID of the thread window, which is equivalent to the ID of the
     * thread related to this window
     *
     * @returns {integer|string}
     */
    getID: function () {
        return this._getThreadID();
    },
    /**
     * @returns {mail.model.Thread|undefined}
     */
    getThread: function () {
        if (!this.hasThread()) {
            return undefined;
        }
        return this._thread;
    },
    /**
     * Get the status of the thread, such as the im status of a DM chat
     * ('online', 'offline', etc.). If this window has no thread, returns
     * `undefined`.
     *
     * @returns {string|undefined}
     */
    getThreadStatus: function () {
        if (!this.hasThread()) {
            return undefined;
        }
        return this._thread.getStatus();
    },
    /**
     * Get the title of the thread window, which usually contains the name of
     * the thread.
     *
     * @returns {string}
     */
    getTitle: function () {
        if (!this.hasThread()) {
            return _t("Undefined");
        }
        return this._thread.getTitle();
    },
    /**
     * Get the unread counter of the related thread. If there are no thread
     * linked to this window, returns 0.
     *
     * @returns {integer}
     */
    getUnreadCounter: function () {
        if (!this.hasThread()) {
            return 0;
        }
        return this._thread.getUnreadCounter();
    },
    /**
     * States whether this thread window is related to a thread or not.
     *
     * This is useful in order to provide specific behaviour for thread windows
     * without any thread, e.g. let them open a thread from this "blank" thread
     * window.
     *
     * @returns {boolean}
     */
    hasThread: function () {
        return !! this._thread;
    },
    /**
     * Tells whether the bottom of the thread in the thread window is visible
     * or not.
     *
     * @returns {boolean}
     */
    isAtBottom: function () {
        return this._threadWidget.isAtBottom();
    },
    /**
     * State whether the related thread is folded or not. If there are no
     * thread related to this window, it means this is the "blank" thread
     * window, therefore we use the internal folded state.
     *
     * @returns {boolean}
     */
    isFolded: function () {
        if (!this.hasThread()) {
            return this._folded;
        }
        return this._thread.isFolded();
    },
    /**
     * States whether the current environment is in mobile or not. This is
     * useful in order to customize the template rendering for mobile view.
     *
     * @returns {boolean}
     */
    isMobile: function () {
        return config.device.isMobile;
    },
    /**
     * States whether the thread window is hidden or not.
     *
     * @returns {boolean}
     */
    isHidden: function () {
        return this._hidden;
    },
    /**
     * States whether the input of the thread window should be displayed or not.
     * By default, any thread window with a thread needs a composer.
     *
     * @returns {boolean}
     */
    needsComposer: function () {
        return this.hasThread();
    },
    /**
     * Render the thread window
     */
    render: function () {
        this.renderHeader();
        if (this.hasThread()) {
            this._threadWidget.render(this._thread, { displayLoadMore: false });
        }
    },
    /**
     * Render the header of this thread window.
     * This is useful when some information on the header have be updated such
     * as the status or the title of the thread that have changed.
     *
     * @private
     */
    renderHeader: function () {
        var options = this._getHeaderRenderingOptions();
        this.$header.html(
            QWeb.render('im_livechat.legacy.mail.AbstractThreadWindow.HeaderContent', options));
    },
    /**
     * Scroll to the bottom of the thread in the thread window
     */
    scrollToBottom: function () {
        this._threadWidget.scrollToBottom();
    },
    /**
     * Toggle the fold state of this thread window. Also update the fold state
     * of the thread model. If the boolean parameter `folded` is provided, it
     * folds/unfolds the window when it is set/unset.
     *
     * @param {boolean} [folded] if not a boolean, toggle the fold state.
     *   Otherwise, fold/unfold the window if set/unset.
     */
    toggleFold: function (folded) {
        if (!_.isBoolean(folded)) {
            folded = !this.isFolded();
        }
        this._updateThreadFoldState(folded);
    },
    /**
     * Update the visual state of the window so that it matched the internal
     * fold state. This is useful in case the related thread has its fold state
     * that has been changed.
     */
    updateVisualFoldState: function () {
        if (!this.isFolded()) {
            this._threadWidget.scrollToBottom();
            if (this.options.autofocus) {
                this._focusInput();
            }
        }
        var height = this.isFolded() ? this.HEIGHT_FOLDED : this.HEIGHT_OPEN;
        this.$el.css({ height: height });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Set the focus on the composer of the thread window. This operation is
     * ignored in mobile context.
     *
     * @private
     * Set the focus on the input of the window
     */
    _focusInput: function () {
        if (
            config.device.touch &&
            config.device.size_class <= config.device.SIZES.SM
        ) {
            return;
        }
        this.$input.focus();
    },
    /**
     * Returns the options used by the rendering of the window's header
     *
     * @private
     * @returns {Object}
     */
    _getHeaderRenderingOptions: function () {
        return {
            status: this.getThreadStatus(),
            thread: this.getThread(),
            title: this.getTitle(),
            unreadCounter: this.getUnreadCounter(),
            widget: this,
        };
    },
    /**
     * Get the ID of the related thread.
     * If this window is not related to a thread, it means this is the "blank"
     * thread window, therefore it returns "_blank" as its ID.
     *
     * @private
     * @returns {integer|string} the threadID, or '_blank' for the window that
     *   is not related to any thread.
     */
    _getThreadID: function () {
        if (!this.hasThread()) {
            return '_blank';
        }
        return this._thread.getID();
    },
    /**
     * Tells whether there is focus on this thread. Note that a thread that has
     * the focus means the input has focus.
     *
     * @private
     * @returns {boolean}
     */
    _hasFocus: function () {
        return this.$input.is(':focus');
    },
    /**
     * Post a message on this thread window, and auto-scroll to the bottom of
     * the thread.
     *
     * @private
     * @param {Object} messageData
     */
    _postMessage: function (messageData) {
        var self = this;
        if (!this.hasThread()) {
            return;
        }
        this._thread.postMessage(messageData)
            .then(function () {
                self._threadWidget.scrollToBottom();
            });
    },
    /**
     * Update the fold state of the thread.
     *
     * This function is called when toggling the fold state of this window.
     * If there is no thread linked to this window, it means this is the
     * "blank" thread window, therefore we use the internal state 'folded'
     *
     * @private
     * @param {boolean} folded
     */
    _updateThreadFoldState: function (folded) {
        if (this.hasThread()) {
            this._thread.fold(folded);
        } else {
            this._folded = folded;
            this.updateVisualFoldState();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Close the thread window.
     * Mark the thread as read if the thread window was open.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickClose: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        if (
            this.hasThread() &&
            this._thread.getUnreadCounter() > 0 &&
            !this.isFolded()
        ) {
            this._thread.markAsRead();
        }
        this.close();
    },
    /**
     * Fold/unfold the thread window.
     * Also mark the thread as read.
     *
     * @private
     */
    _onClickFold: function () {
        if (!config.device.isMobile) {
            this.toggleFold();
        }
    },
    /**
     * Called when the composer is clicked -> forces focus on input even if
     * jquery's blockUI is enabled.
     *
     * @private
     * @param {Event} ev
     */
    _onComposerClick: function (ev) {
        if ($(ev.target).closest('a, button').length) {
            return;
        }
        this._focusInput();
    },
    /**
     * @private
     */
    _onDocumentViewerClose: function () {
        this._focusInput();
    },
    /**
     * Called when typing something on the composer of this thread window.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown: function (ev) {
        ev.stopPropagation(); // to prevent jquery's blockUI to cancel event
        // ENTER key (avoid requiring jquery ui for external livechat)
        if (ev.which === 13) {
            var content = _.str.trim(this.$input.val());
            var messageData = {
                content: content,
                attachment_ids: [],
                partner_ids: [],
            };
            this.$input.val('');
            if (content) {
                this._postMessage(messageData);
            }
        }
    },
    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeypress: function (ev) {
        ev.stopPropagation(); // to prevent jquery's blockUI to cancel event
    },
    /**
     * @private
     */
    _onScroll: function () {
        if (this.hasThread() && this.isAtBottom()) {
            this._thread.markAsRead();
        }
    },
    /**
     * When a thread window is clicked on, we want to give the focus to the main
     * input. An exception is made when the user is selecting something.
     *
     * @private
     */
    _onThreadWindowClicked: function () {
        var selectObj = window.getSelection();
        if (selectObj.anchorOffset === selectObj.focusOffset) {
            this.$input.focus();
        }
    },
});

return AbstractThreadWindow;

});

odoo.define('im_livechat.legacy.mail.model.AbstractThread', function (require) {
"use strict";

var Class = require('web.Class');
var Mixins = require('web.mixins');

/**
 * Abstract thread is the super class of all threads, either backend threads
 * (which are compatible with mail service) or website livechats.
 *
 * Abstract threads contain abstract messages
 */
var AbstractThread = Class.extend(Mixins.EventDispatcherMixin, {
    /**
     * @param {Object} params
     * @param {Object} params.data
     * @param {integer|string} params.data.id the ID of this thread
     * @param {string} params.data.name the name of this thread
     * @param {string} [params.data.status=''] the status of this thread
     * @param {Object} params.parent Object with the event-dispatcher mixin
     *   (@see {web.mixins.EventDispatcherMixin})
     */
    init: function (params) {
        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(params.parent);

        this._folded = false; // threads are unfolded by default
        this._id = params.data.id;
        this._name = params.data.name;
        this._status = params.data.status || '';
        this._unreadCounter = 0; // amount of messages not yet been read
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a message to this thread.
     *
     * @param {im_livechat.legacy.mail.model.AbstractMessage} message
     */
    addMessage: function (message) {
        this._addMessage.apply(this, arguments);
        this.trigger('message_added', message);
    },
    /**
     * Updates the folded state of the thread
     *
     * @param {boolean} folded
     */
    fold: function (folded) {
        this._folded = folded;
    },
    /**
     * Get the ID of this thread
     *
     * @returns {integer|string}
     */
    getID: function () {
        return this._id;
    },
    /**
     * @abstract
     * @returns {im_livechat.legacy.mail.model.AbstractMessage[]}
     */
    getMessages: function () {},
    /**
     * Get the name of this thread. If the name of the thread has been created
     * by the user from an input, it may be escaped.
     *
     * @returns {string}
     */
    getName: function () {
        return this._name;
    },
    /**
     * Get the status of the thread (e.g. 'online', 'offline', etc.)
     *
     * @returns {string}
     */
    getStatus: function () {
        return this._status;
    },
    /**
     * Returns the title to display in thread window's headers.
     *
     * @returns {string} the name of the thread by default (see @getName)
     */
    getTitle: function () {
        return this.getName();
    },
    getType: function () {},
    /**
     * @returns {integer}
     */
    getUnreadCounter: function () {
        return this._unreadCounter;
    },
    /**
     * @returns {boolean}
     */
    hasMessages: function () {
        return !_.isEmpty(this.getMessages());
    },
    /**
     * States whether this thread is compatible with the 'seen' feature.
     * By default, threads do not have thsi feature active.
     * @see {im_livechat.legacy.mail.model.ThreadSeenMixin} to enable this feature on a thread.
     *
     * @returns {boolean}
     */
    hasSeenFeature: function () {
        return false;
    },
    /**
     * States whether this thread is folded or not.
     *
     * @return {boolean}
     */
    isFolded: function () {
        return this._folded;
    },
    /**
     * Mark the thread as read, which resets the unread counter to 0. This is
     * only performed if the unread counter is not 0.
     *
     * @returns {Promise}
     */
    markAsRead: function () {
        if (this._unreadCounter > 0) {
            return this._markAsRead();
        }
        return Promise.resolve();
    },
    /**
     * Post a message on this thread
     *
     * @returns {Promise} resolved with the message object to be sent to the
     *   server
     */
    postMessage: function () {
        return this._postMessage.apply(this, arguments)
                                .then(this.trigger.bind(this, 'message_posted'));
    },
    /**
     * Resets the unread counter of this thread to 0.
     */
    resetUnreadCounter: function () {
        this._unreadCounter = 0;
        this._warnUpdatedUnreadCounter();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a message to this thread.
     *
     * @abstract
     * @private
     * @param {im_livechat.legacy.mail.model.AbstractMessage} message
     */
    _addMessage: function (message) {},
    /**
     * Increments the unread counter of this thread by 1 unit.
     *
     * @private
     */
    _incrementUnreadCounter: function () {
        this._unreadCounter++;
    },
    /**
     * Mark the thread as read
     *
     * @private
     * @returns {Promise}
     */
    _markAsRead: function () {
        this.resetUnreadCounter();
        return Promise.resolve();
    },
    /**
     * Post a message on this thread
     *
     * @abstract
     * @private
     * @returns {Promise} resolved with the message object to be sent to the
     *   server
     */
    _postMessage: function () {
        return Promise.resolve();
    },
    /**
     * Warn views (e.g. discuss app, thread window, etc.) to update visually
     * the unread counter of this thread.
     *
     * @abstract
     * @private
     */
    _warnUpdatedUnreadCounter: function () {},
});

return AbstractThread;

});
