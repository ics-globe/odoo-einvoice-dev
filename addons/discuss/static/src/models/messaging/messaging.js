/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr, many2many, many2one, one2many, one2one } from '@discuss/model/model_field';
import { create, replace } from '@discuss/model/model_field_command';

function factory(dependencies) {

    class Messaging extends dependencies['discuss.model'] {

        /**
         * @override
         */
        _willDelete() {
            if (this.env.services['bus_service']) {
                this.env.services['bus_service'].off('window_focus', null, this._handleGlobalWindowFocus);
            }
            return super._willDelete(...arguments);
        }

        /**
         * Starts messaging and related records.
         */
        async start() {
            this._handleGlobalWindowFocus = this._handleGlobalWindowFocus.bind(this);
            this.env.services['bus_service'].on('window_focus', null, this._handleGlobalWindowFocus);
            await this.async(() => this.initializer.start());
            this.notificationHandler.start();
            this.update({ isInitialized: true });
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Open the form view of the record with provided id and model.
         * Gets the chat with the provided person and returns it.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @param {Object} param0
         * @param {integer} [param0.partnerId]
         * @param {integer} [param0.userId]
         * @param {Object} [options]
         * @returns {discuss.channel|undefined}
         */
        async getChat({ partnerId, userId }) {
            if (userId) {
                const user = this.env.models['res.users'].insert({ id: userId });
                return user.getChat();
            }
            if (partnerId) {
                const partner = this.env.models['res.partner'].insert({ id: partnerId });
                return partner.getChat();
            }
        }

        /**
         * Opens a chat with the provided person and returns it.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @param {Object} person forwarded to @see `getChat()`
         * @param {Object} [options] forwarded to @see `discuss.channel:open()`
         * @returns {discuss.channel|undefined}
         */
        async openChat(person, options) {
            const chat = await this.async(() => this.getChat(person));
            if (!chat) {
                return;
            }
            await this.async(() => chat.open(options));
            return chat;
        }

        /**
         * Opens the form view of the record with provided id and model.
         *
         * @param {Object} param0
         * @param {integer} param0.id
         * @param {string} param0.model
         */
        async openDocument({ id, model }) {
            this.env.bus.trigger('do-action', {
                action: {
                    type: 'ir.actions.act_window',
                    res_model: model,
                    views: [[false, 'form']],
                    res_id: id,
                },
            });
            if (this.env.messaging.device.isMobile) {
                // messaging menu has a higher z-index than views so it must
                // be closed to ensure the visibility of the view
                this.env.messaging.messagingMenu.close();
            }
        }

        /**
         * Opens the most appropriate view that is a profile for provided id and
         * model.
         *
         * @param {Object} param0
         * @param {integer} param0.id
         * @param {string} param0.model
         */
        async openProfile({ id, model }) {
            if (model === 'res.partner') {
                const partner = this.env.models['res.partner'].insert({ id });
                return partner.openProfile();
            }
            if (model === 'res.users') {
                const user = this.env.models['res.users'].insert({ id });
                return user.openProfile();
            }
            // TODO SEB adapt, no such thing as a channel profile (just open the channel)
            if (model === 'discuss.channel') {
                let channel = this.env.models['discuss.channel'].findFromIdentifyingData({ id, model: 'discuss.channel' });
                if (!channel) {
                    channel = (await this.async(() =>
                        this.env.models['discuss.channel'].performRpcChannelInfo({ ids: [id] })
                    ))[0];
                }
                if (!channel) {
                    this.env.services['notification'].notify({
                        message: this.env._t("You can only open the profile of existing channels."),
                        type: 'warning',
                    });
                    return;
                }
                return channel.openProfile();
            }
            return this.env.messaging.openDocument({ id, model });
        }

        /**
         * Refreshes the value of `isNotificationPermissionDefault`.
         *
         * Must be called in flux-specific way because the browser does not
         * provide an API to detect when this value changes.
         */
        refreshIsNotificationPermissionDefault() {
            this.update({ isNotificationPermissionDefault: this._computeIsNotificationPermissionDefault() });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _computeAllPinnedChannels() {
            return replace(this.allChannels.filter(channel => channel.isPinned));
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsNotificationPermissionDefault() {
            const browserNotification = this.env.browser.Notification;
            return browserNotification ? browserNotification.permission === 'default' : false;
        }

        /**
         * @private
         */
        _handleGlobalWindowFocus() {
            this.update({ outOfFocusUnreadMessageCounter: 0 });
            this.env.bus.trigger('set_title_part', {
                part: '_chat',
            });
        }

    }

    Messaging.fields = {
        /**
         * States all known channels.
         */
        allChannels: one2many('discuss.channel', {
            inverse: 'messaging',
            readonly: true,
        }),
        /**
         * Serves as compute dependency.
         */
        allChannelsIsPinned: attr({
            related: 'allChannels.isPinned',
        }),
        /**
         * States all known pinned channels.
         */
         // TODO SEB rename "for current user"?
        allPinnedChannels: one2many('discuss.channel', {
            compute: '_computeAllPinnedChannels',
            dependencies: [
                'allChannels',
                'allChannelsIsPinned',
            ],
            readonly: true,
        }),
        cannedResponses: one2many('discuss.canned_response'),
        chatWindowManager: one2one('discuss.chat_window_manager', {
            default: create(),
            inverse: 'messaging',
            isCausal: true,
            readonly: true,
        }),
        commands: one2many('discuss.channel_command'),
        currentPartner: one2one('res.partner'),
        currentUser: one2one('res.users'),
        device: one2one('discuss.device', {
            default: create(),
            isCausal: true,
            readonly: true,
        }),
        dialogManager: one2one('discuss.dialog_manager', {
            default: create(),
            isCausal: true,
            readonly: true,
        }),
        discuss: one2one('discuss.discuss', {
            default: create(),
            inverse: 'messaging',
            isCausal: true,
            readonly: true,
        }),
        initializer: one2one('discuss.messaging_initializer', {
            default: create(),
            inverse: 'messaging',
            isCausal: true,
            readonly: true,
        }),
        isInitialized: attr({
            default: false,
        }),
        /**
         * States whether browser Notification Permission is currently in its
         * 'default' state. This means it is allowed to make a request to the
         * user to enable notifications.
         */
        isNotificationPermissionDefault: attr({
            compute: '_computeIsNotificationPermissionDefault',
        }),
        locale: one2one('discuss.locale', {
            default: create(),
            isCausal: true,
            readonly: true,
        }),
        messagingMenu: one2one('discuss.messaging_menu', {
            default: create(),
            inverse: 'messaging',
            isCausal: true,
            readonly: true,
        }),
        // TODO SEB move into mail
        // notificationGroupManager: one2one('mail.notification_group_manager', {
        //     default: create(),
        //     isCausal: true,
        //     readonly: true,
        // }),
        notificationHandler: one2one('discuss.messaging_notification_handler', {
            default: create(),
            inverse: 'messaging',
            isCausal: true,
            readonly: true,
        }),
        outOfFocusUnreadMessageCounter: attr({
            default: 0,
        }),
        partnerRoot: many2one('res.partner'),
        /**
         * Determines which partners should be considered the public partners,
         * which are special partners notably used in livechat.
         */
        publicPartners: many2many('res.partner'),
        /**
         * Mailbox Starred.
         */
        starred: one2one('discuss.channel'),
    };

    Messaging.modelName = 'discuss.messaging';

    return Messaging;
}

registerNewModel('discuss.messaging', factory);
