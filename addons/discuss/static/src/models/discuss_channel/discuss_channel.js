/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr, many2many, many2one, one2many, one2one } from '@discuss/model/model_field';
import { clear, create, insert, link, replace, unlink, unlinkAll } from '@discuss/model/model_field_command';
import throttle from '@discuss/utils/throttle/throttle';
import Timer from '@discuss/utils/timer/timer';
import { cleanSearchTerm } from '@discuss/utils/utils';

function factory(dependencies) {

    class DiscussChannel extends dependencies['discuss.model'] {

        /**
         * @override
         */
        _willCreate() {
            const res = super._willCreate(...arguments);
            /**
             * Timer of current partner that was currently typing something, but
             * there is no change on the input for 5 seconds. This is used
             * in order to automatically notify other members that current
             * partner has stopped typing something, due to making no changes
             * on the composer for some time.
             */
            this._currentPartnerInactiveTypingTimer = new Timer(
                this.env,
                () => this.async(() => this._onCurrentPartnerInactiveTypingTimeout()),
                5 * 1000
            );
            /**
             * Last 'is_typing' status of current partner that has been notified
             * to other members. Useful to prevent spamming typing notifications
             * to other members if it hasn't changed. An exception is the
             * current partner long typing scenario where current partner has
             * to re-send the same typing notification from time to time, so
             * that other members do not assume he/she is no longer typing
             * something from not receiving any typing notifications for a
             * very long time.
             *
             * Supported values: true/false/undefined.
             * undefined makes only sense initially and during current partner
             * long typing timeout flow.
             */
            this._currentPartnerLastNotifiedIsTyping = undefined;
            /**
             * Timer of current partner that is typing a very long text. When
             * the other members do not receive any typing notification for a
             * long time, they must assume that the related partner is no longer
             * typing something (e.g. they have closed the browser tab).
             * This is a timer to let other members know that current partner
             * is still typing something, so that they should not assume he/she
             * has stopped typing something.
             */
            this._currentPartnerLongTypingTimer = new Timer(
                this.env,
                () => this.async(() => this._onCurrentPartnerLongTypingTimeout()),
                50 * 1000
            );
            /**
             * Determines whether the next request to notify current partner
             * typing status should always result to making RPC, regardless of
             * whether last notified current partner typing status is the same.
             * Most of the time we do not want to notify if value hasn't
             * changed, exception being the long typing scenario of current
             * partner.
             */
            this._forceNotifyNextCurrentPartnerTypingStatus = false;
            /**
             * Registry of timers of partners currently typing in the channel,
             * excluding current partner. This is useful in order to
             * automatically unregister typing members when not receive any
             * typing notification after a long time. Timers are internally
             * indexed by partner records as key. The current partner is
             * ignored in this registry of timers.
             *
             * @see registerOtherMemberTypingMember
             * @see unregisterOtherMemberTypingMember
             */
            this._otherMembersLongTypingTimers = new Map();

            /**
             * Clearable and cancellable throttled version of the
             * `_notifyCurrentPartnerTypingStatus` method.
             * This is useful when the current partner posts a message and
             * types something else afterwards: it must notify immediately that
             * he/she is typing something, instead of waiting for the throttle
             * internal timer.
             *
             * @see _notifyCurrentPartnerTypingStatus
             */
            this._throttleNotifyCurrentPartnerTypingStatus = throttle(
                this.env,
                ({ isTyping }) => this.async(() => this._notifyCurrentPartnerTypingStatus({ isTyping })),
                2.5 * 1000
            );
            return res;
        }

        /**
         * @override
         */
        _willDelete() {
            this._currentPartnerInactiveTypingTimer.clear();
            this._currentPartnerLongTypingTimer.clear();
            this._throttleNotifyCurrentPartnerTypingStatus.clear();
            for (const timer of this._otherMembersLongTypingTimers.values()) {
                timer.clear();
            }
            if (this.isTemporary) {
                for (const message of this.messages) {
                    message.delete();
                }
            }
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {discuss.channel} [channel] the concerned channel
         */
        static computeLastCurrentPartnerMessageSeenByEveryone(channel = undefined) {
            const channels = channel ? [channel] : this.env.models['discuss.channel'].all();
            channels.map(channel => {
                channel.update({
                    lastCurrentPartnerMessageSeenByEveryone: channel._computeLastCurrentPartnerMessageSeenByEveryone(),
                });
            });
        }

        /**
         * Fetches channels matching the given composer search state to extend
         * the JS knowledge and to update the suggestion list accordingly.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {discuss.channel} [options.channel] prioritize and/or restrict
         *  result in the context of given channel
         */
        static async fetchSuggestions(searchTerm, { channel } = {}) {
            const channelsData = await this.env.services.rpc(
                {
                    model: 'discuss.channel',
                    method: 'get_mention_suggestions',
                    kwargs: { search: searchTerm },
                },
                { shadow: true },
            );
            this.env.models['discuss.channel'].insert(channelsData);
        }

        /**
         * Returns a sort function to determine the order of display of channels
         * in the suggestion list.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {discuss.channel} [options.channel] prioritize result in the
         *  context of given channel
         * @returns {function}
         */
        static getSuggestionSortFunction(searchTerm, { channel } = {}) {
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            return (a, b) => {
                const isAPublic = a.model === 'discuss.channel' && a.public === 'public';
                const isBPublic = b.model === 'discuss.channel' && b.public === 'public';
                if (isAPublic && !isBPublic) {
                    return -1;
                }
                if (!isAPublic && isBPublic) {
                    return 1;
                }
                const isMemberOfA = a.model === 'discuss.channel' && a.members.includes(this.env.messaging.currentPartner);
                const isMemberOfB = b.model === 'discuss.channel' && b.members.includes(this.env.messaging.currentPartner);
                if (isMemberOfA && !isMemberOfB) {
                    return -1;
                }
                if (!isMemberOfA && isMemberOfB) {
                    return 1;
                }
                const cleanedAName = cleanSearchTerm(a.name || '');
                const cleanedBName = cleanSearchTerm(b.name || '');
                if (cleanedAName.startsWith(cleanedSearchTerm) && !cleanedBName.startsWith(cleanedSearchTerm)) {
                    return -1;
                }
                if (!cleanedAName.startsWith(cleanedSearchTerm) && cleanedBName.startsWith(cleanedSearchTerm)) {
                    return 1;
                }
                if (cleanedAName < cleanedBName) {
                    return -1;
                }
                if (cleanedAName > cleanedBName) {
                    return 1;
                }
                return a.id - b.id;
            };
        }

        /**
         * Load the previews of the specified channels. Basically, it fetches the
         * last messages, since they are used to display inline content of them.
         *
         * @static
         * @param {discuss.channel[]} channels
         */
        static async loadPreviews(channels) {
            if (channels.length === 0) {
                return;
            }
            const channelPreviews = await this.env.services.rpc({
                model: 'discuss.channel',
                method: 'channel_fetch_preview',
                args: [channels.map(channel => channel.id)],
            }, { shadow: true });
            this.env.models['discuss.channel.message'].insert(channelPreviews.filter(p => p.last_message).map(
                channelPreview => channelPreview.last_message
            ));
        }


        /**
         * Performs the `channel_fold` RPC on `discuss.channel`.
         *
         * @static
         * @param {string} uuid
         * @param {string} state
         */
        static async performRpcChannelFold(uuid, state) {
            return this.env.services.rpc({
                model: 'discuss.channel',
                method: 'channel_fold',
                kwargs: {
                    state,
                    uuid,
                }
            }, { shadow: true });
        }

        /**
         * Performs the `channel_info` RPC on `discuss.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {integer[]} param0.ids list of id of channels
         * @returns {discuss.channel[]}
         */
        static async performRpcChannelInfo({ ids }) {
            const channelInfos = await this.env.services.rpc({
                model: 'discuss.channel',
                method: 'channel_info',
                args: [ids],
            }, { shadow: true });
            const channels = this.env.models['discuss.channel'].insert(channelInfos);
            return channels;
        }

        /**
         * Performs the `channel_seen` RPC on `discuss.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {integer[]} param0.ids list of id of channels
         * @param {integer[]} param0.lastMessageId
         */
        static async performRpcChannelSeen({ ids, lastMessageId }) {
            return this.env.services.rpc({
                model: 'discuss.channel',
                method: 'channel_seen',
                args: [ids],
                kwargs: {
                    last_message_id: lastMessageId,
                },
            }, { shadow: true });
        }

        /**
         * Performs the `channel_pin` RPC on `discuss.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {boolean} [param0.pinned=false]
         * @param {string} param0.uuid
         */
        static async performRpcChannelPin({ pinned = false, uuid }) {
            return this.env.services.rpc({
                model: 'discuss.channel',
                method: 'channel_pin',
                kwargs: {
                    uuid,
                    pinned,
                },
            }, { shadow: true });
        }

        /**
         * Performs the `channel_create` RPC on `discuss.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {string} param0.name
         * @param {string} [param0.privacy]
         * @returns {discuss.channel} the created channel
         */
        static async performRpcCreateChannel({ name, privacy }) {
            const device = this.env.messaging.device;
            const data = await this.env.services.rpc({
                model: 'discuss.channel',
                method: 'channel_create',
                args: [name, privacy],
                kwargs: {
                    context: Object.assign({}, this.env.session.user_content, {
                        // optimize the return value by avoiding useless queries
                        // in non-mobile devices
                        isMobile: device.isMobile,
                    }),
                },
            });
            return this.env.models['discuss.channel'].insert(data);
        }

        /**
         * Performs the `channel_get` RPC on `discuss.channel`.
         *
         * `openChat` is preferable in business code because it will avoid the
         * RPC if the chat already exists.
         *
         * @static
         * @param {Object} param0
         * @param {integer[]} param0.partnerIds
         * @param {boolean} [param0.pinForCurrentPartner]
         * @returns {discuss.channel|undefined} the created or existing chat
         */
        static async performRpcCreateChat({ partnerIds, pinForCurrentPartner }) {
            const device = this.env.messaging.device;
            // TODO FIX: potential duplicate chat task-2276490
            const data = await this.env.services.rpc({
                model: 'discuss.channel',
                method: 'channel_get',
                kwargs: {
                    context: Object.assign({}, this.env.session.user_content, {
                        // optimize the return value by avoiding useless queries
                        // in non-mobile devices
                        isMobile: device.isMobile,
                    }),
                    partners_to: partnerIds,
                    pin: pinForCurrentPartner,
                },
            });
            if (!data) {
                return;
            }
            return this.env.models['discuss.channel'].insert(data);
        }

        /**
         * Performs the `channel_join_and_get_info` RPC on `discuss.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {integer} param0.channelId
         * @returns {discuss.channel} the channel that was joined
         */
        static async performRpcJoinChannel({ channelId }) {
            const device = this.env.messaging.device;
            const data = await this.env.services.rpc({
                model: 'discuss.channel',
                method: 'channel_join_and_get_info',
                args: [[channelId]],
                kwargs: {
                    context: Object.assign({}, this.env.session.user_content, {
                        // optimize the return value by avoiding useless queries
                        // in non-mobile devices
                        isMobile: device.isMobile,
                    }),
                },
            });
            return this.env.models['discuss.channel'].insert(data);
        }

        /**
         * Performs the `execute_command` RPC on `discuss.channel`.
         *
         * @static
         * @param {Object} param0
         * @param {integer} param0.channelId
         * @param {string} param0.command
         * @param {Object} [param0.postData={}]
         */
        static async performRpcExecuteCommand({ channelId, command, postData = {} }) {
            return this.env.services.rpc({
                model: 'discuss.channel',
                method: 'execute_command',
                args: [[channelId]],
                kwargs: Object.assign({ command }, postData),
            });
        }

        /**
         * Performs the `message_post` RPC on given channelModel.
         *
         * @static
         * @param {Object} param0
         * @param {Object} param0.postData
         * @param {integer} param0.channelId
         * @param {string} param0.channelModel
         * @return {integer} the posted message id
         */
        static async performRpcMessagePost({ postData, channelId, channelModel }) {
            return this.env.services.rpc({
                model: 'discuss.channel',
                method: 'message_post',
                args: [channelId],
                kwargs: postData,
            });
        }

        /*
         * Returns channels that match the given search term. More specially only
         * channels of model 'discuss.channel' are suggested, and if the context
         * channel is a private channel, only itself is returned if it matches
         * the search term.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {discuss.channel} [options.channel] prioritize and/or restrict
         *  result in the context of given channel
         * @returns {[discuss.channels[], discuss.channels[]]}
         */
        static searchSuggestions(searchTerm, { channel } = {}) {
            let channels;
            if (channel && channel.public !== 'public') {
                // Only return the current channel when in the context of a
                // non-public channel. Indeed, the message with the mention
                // would appear in the target channel, so this prevents from
                // inadvertently leaking the private message into the mentioned
                // channel.
                channels = [channel];
            } else {
                channels = this.env.models['discuss.channel'].all();
            }
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            return [channels.filter(channel =>
                !channel.isTemporary &&
                channel.channel_type === 'channel' &&
                channel.displayName &&
                cleanSearchTerm(channel.displayName).includes(cleanedSearchTerm)
            )];
        }

        /**
         * @param {string} [stringifiedDomain='[]']
         * @returns {discuss.channel_cache}
         */
        cache(stringifiedDomain = '[]') {
            return this.env.models['discuss.channel_cache'].insert({
                stringifiedDomain,
                channel: link(this),
            });
        }

        /**
         * Returns the text that identifies this channel in a mention.
         *
         * @returns {string}
         */
        getMentionText() {
            return this.name;
        }

        /**
         * Load new messages on the main cache of this channel.
         */
        loadNewMessages() {
            this.mainCache.loadNewMessages();
        }

        /**
         * Mark the specified conversation as fetched.
         */
        async markAsFetched() {
            await this.async(() => this.env.services.rpc({
                model: 'discuss.channel',
                method: 'channel_fetched',
                args: [[this.id]],
            }, { shadow: true }));
        }

        /**
         * Mark the specified conversation as read/seen.
         *
         * @param {discuss.channel.message} message the message to be considered as last seen.
         */
        async markAsSeen(message) {
            if (this.pendingSeenMessageId && message.id <= this.pendingSeenMessageId) {
                return;
            }
            if (
                this.lastSeenByCurrentPartnerMessageId &&
                message.id <= this.lastSeenByCurrentPartnerMessageId
            ) {
                return;
            }
            this.update({ pendingSeenMessageId: message.id });
            return this.env.models['discuss.channel'].performRpcChannelSeen({
                ids: [this.id],
                lastMessageId: message.id,
            });
        }

        /**
         * Marks as read all needaction messages of this channel.
         */
        async markNeedactionMessagesAsRead() {
            await this.async(() =>
                this.env.models['discuss.channel.message'].markAsRead(this.needactionMessages)
            );
        }

        /**
         * Notifies the server of new fold state. Useful for initial,
         * cross-tab, and cross-device chat window state synchronization.
         *
         * @param {string} state
         */
        async notifyFoldStateToServer(state) {
            if (!this.uuid) {
                return;
            }
            return this.env.models['discuss.channel'].performRpcChannelFold(this.uuid, state);
        }

        /**
         * Notify server to leave the current channel. Useful for cross-tab
         * and cross-device chat window state synchronization.
         *
         * Only makes sense if isPendingPinned is set to the desired value.
         */
        async notifyPinStateToServer() {
            if (this.isPendingPinned) {
                await this.env.models['discuss.channel'].performRpcChannelPin({
                    pinned: true,
                    uuid: this.uuid,
                });
            } else {
                this.env.models['discuss.channel'].performRpcExecuteCommand({
                    channelId: this.id,
                    command: 'leave',
                });
            }
        }

        /**
         * Opens this channel either as form view, in discuss app, or as a chat
         * window. The channel will be opened in an "active" matter, which will
         * interrupt current user flow.
         *
         * @param {Object} [param0]
         * @param {boolean} [param0.expanded=false]
         */
        async open({ expanded = false } = {}) {
            const discuss = this.env.messaging.discuss;
            // check if channel must be opened in discuss
            const device = this.env.messaging.device;
            if (
                (!device.isMobile && (discuss.isOpen || expanded)) ||
                this.model === 'discuss.box'
            ) {
                return discuss.openChannel(this);
            }
            // channel must be opened in chat window
            return this.env.messaging.chatWindowManager.openChannel(this, {
                makeActive: true,
            });
        }

        /**
         * Pin this channel and notify server of the change.
         */
        async pin() {
            this.update({ isPendingPinned: true });
            await this.notifyPinStateToServer();
        }

        async refresh() {
            this.loadNewMessages();
        }

        /**
         * Refresh the typing status of the current partner.
         */
        refreshCurrentPartnerIsTyping() {
            this._currentPartnerInactiveTypingTimer.reset();
        }

        /**
         * Called to refresh a registered other member partner that is typing
         * something.
         *
         * @param {res.partner} partner
         */
        refreshOtherMemberTypingMember(partner) {
            this._otherMembersLongTypingTimers.get(partner).reset();
        }

        /**
         * Called when current partner is inserting some input in composer.
         * Useful to notify current partner is currently typing something in the
         * composer of this channel to all other members.
         */
        async registerCurrentPartnerIsTyping() {
            // Handling of typing timers.
            this._currentPartnerInactiveTypingTimer.start();
            this._currentPartnerLongTypingTimer.start();
            // Manage typing member relation.
            const currentPartner = this.env.messaging.currentPartner;
            const newOrderedTypingMemberLocalIds = this.orderedTypingMemberLocalIds
                .filter(localId => localId !== currentPartner.localId);
            newOrderedTypingMemberLocalIds.push(currentPartner.localId);
            this.update({
                orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                typingMembers: link(currentPartner),
            });
            // Notify typing status to other members.
            await this._throttleNotifyCurrentPartnerTypingStatus({ isTyping: true });
        }

        /**
         * Called to register a new other member partner that is typing
         * something.
         *
         * @param {res.partner} partner
         */
        registerOtherMemberTypingMember(partner) {
            const timer = new Timer(
                this.env,
                () => this.async(() => this._onOtherMemberLongTypingTimeout(partner)),
                60 * 1000
            );
            this._otherMembersLongTypingTimers.set(partner, timer);
            timer.start();
            const newOrderedTypingMemberLocalIds = this.orderedTypingMemberLocalIds
                .filter(localId => localId !== partner.localId);
            newOrderedTypingMemberLocalIds.push(partner.localId);
            this.update({
                orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                typingMembers: link(partner),
            });
        }

        /**
         * Rename the given channel with provided new name.
         *
         * @param {string} newName
         */
        async rename(newName) {
            if (this.channel_type === 'chat') {
                await this.async(() => this.env.services.rpc({
                    model: 'discuss.channel',
                    method: 'channel_set_custom_name',
                    args: [this.id],
                    kwargs: {
                        name: newName,
                    },
                }));
            }
            this.update({ custom_channel_name: newName });
        }

        /**
         * Unpin this channel and notify server of the change.
         */
        async unpin() {
            this.update({ isPendingPinned: false });
            await this.notifyPinStateToServer();
        }

        /**
         * Called when current partner has explicitly stopped inserting some
         * input in composer. Useful to notify current partner has currently
         * stopped typing something in the composer of this channel to all other
         * members.
         *
         * @param {Object} [param0={}]
         * @param {boolean} [param0.immediateNotify=false] if set, is typing
         *   status of current partner is immediately notified and doesn't
         *   consume throttling at all.
         */
        async unregisterCurrentPartnerIsTyping({ immediateNotify = false } = {}) {
            // Handling of typing timers.
            this._currentPartnerInactiveTypingTimer.clear();
            this._currentPartnerLongTypingTimer.clear();
            // Manage typing member relation.
            const currentPartner = this.env.messaging.currentPartner;
            const newOrderedTypingMemberLocalIds = this.orderedTypingMemberLocalIds
                .filter(localId => localId !== currentPartner.localId);
            this.update({
                orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                typingMembers: unlink(currentPartner),
            });
            // Notify typing status to other members.
            if (immediateNotify) {
                this._throttleNotifyCurrentPartnerTypingStatus.clear();
            }
            await this.async(
                () => this._throttleNotifyCurrentPartnerTypingStatus({ isTyping: false })
            );
        }

        /**
         * Called to unregister an other member partner that is no longer typing
         * something.
         *
         * @param {res.partner} partner
         */
        unregisterOtherMemberTypingMember(partner) {
            this._otherMembersLongTypingTimers.get(partner).clear();
            this._otherMembersLongTypingTimers.delete(partner);
            const newOrderedTypingMemberLocalIds = this.orderedTypingMemberLocalIds
                .filter(localId => localId !== partner.localId);
            this.update({
                orderedTypingMemberLocalIds: newOrderedTypingMemberLocalIds,
                typingMembers: unlink(partner),
            });
        }

        /**
         * Unsubscribe current user from provided channel.
         */
        unsubscribe() {
            this.env.messaging.chatWindowManager.closeChannel(this);
            this.unpin();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId({ id }) {
            return `${this.modelName}_${id}`;
        }

        /**
         * @private
         * @returns {res.partner}
         */
        _computeCorrespondent() {
            if (this.channel_type === 'channel') {
                return unlink();
            }
            const correspondents = this.members.filter(partner =>
                partner !== this.env.messaging.currentPartner
            );
            if (correspondents.length === 1) {
                // 2 members chat
                return link(correspondents[0]);
            }
            if (this.members.length === 1) {
                // chat with oneself
                return link(this.members[0]);
            }
            return unlink();
        }

        /**
         * @private
         * @returns {string}
         */
        _computeDisplayName() {
            if (this.channel_type === 'chat' && this.correspondent) {
                return this.custom_channel_name || this.correspondent.nameOrDisplayName;
            }
            return this.name;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasSeenIndicators() {
            if (this.model !== 'discuss.channel') {
                return false;
            }
            return ['chat', 'livechat'].includes(this.channel_type);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsChatChannel() {
            return this.channel_type === 'chat';
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsPinned() {
            return this.isPendingPinned !== undefined ? this.isPendingPinned : this.isServerPinned;
        }

        /**
         * @private
         * @returns {discuss.channel.message}
         */
        _computeLastCurrentPartnerMessageSeenByEveryone() {
            const otherPartnerSeenInfos =
                this.partnerSeenInfos.filter(partnerSeenInfo =>
                    partnerSeenInfo.partner !== this.messagingCurrentPartner);
            if (otherPartnerSeenInfos.length === 0) {
                return unlinkAll();
            }

            const otherPartnersLastSeenMessageIds =
                otherPartnerSeenInfos.map(partnerSeenInfo =>
                    partnerSeenInfo.lastSeenMessage ? partnerSeenInfo.lastSeenMessage.id : 0
                );
            if (otherPartnersLastSeenMessageIds.length === 0) {
                return unlinkAll();
            }
            const lastMessageSeenByAllId = Math.min(
                ...otherPartnersLastSeenMessageIds
            );
            const currentPartnerOrderedSeenMessages =
                this.orderedMessages.filter(message =>
                    message.author === this.messagingCurrentPartner &&
                    message.id <= lastMessageSeenByAllId);

            if (
                !currentPartnerOrderedSeenMessages ||
                currentPartnerOrderedSeenMessages.length === 0
            ) {
                return unlinkAll();
            }
            return link(currentPartnerOrderedSeenMessages.slice().pop());
        }

        /**
         * @private
         * @returns {discuss.channel.message|undefined}
         */
        _computeLastMessage() {
            const {
                length: l,
                [l - 1]: lastMessage,
            } = this.orderedMessages;
            if (lastMessage) {
                return link(lastMessage);
            }
            return unlink();
        }

        /**
         * Adjusts the last seen message received from the server to consider
         * the following messages also as read if they are messages from the
         * current partner.
         *
         * @private
         * @returns {integer}
         */
        _computeLastSeenByCurrentPartnerMessageId() {
            const firstMessage = this.orderedMessages[0];
            if (
                firstMessage &&
                this.lastSeenByCurrentPartnerMessageId &&
                this.lastSeenByCurrentPartnerMessageId < firstMessage.id
            ) {
                // no deduction can be made if there is a gap
                return this.lastSeenByCurrentPartnerMessageId;
            }
            let lastSeenByCurrentPartnerMessageId = this.lastSeenByCurrentPartnerMessageId;
            for (const message of this.orderedMessages) {
                if (message.id <= this.lastSeenByCurrentPartnerMessageId) {
                    continue;
                }
                if (message.author === this.env.messaging.currentPartner) {
                    lastSeenByCurrentPartnerMessageId = message.id;
                    continue;
                }
                return lastSeenByCurrentPartnerMessageId;
            }
            return lastSeenByCurrentPartnerMessageId;
        }

        /**
         * @private
         * @returns {discuss.channel.message|undefined}
         */
        _computeLastNeedactionMessage() {
            const orderedNeedactionMessages = this.needactionMessages.sort(
                (m1, m2) => m1.id < m2.id ? -1 : 1
            );
            const {
                length: l,
                [l - 1]: lastNeedactionMessage,
            } = orderedNeedactionMessages;
            if (lastNeedactionMessage) {
                return link(lastNeedactionMessage);
            }
            return unlink();
        }

        /**
         * @private
         * @returns {discuss.channel_cache}
         */
        _computeMainCache() {
            return insert({
                stringifiedDomain: '[]',
                channel: link(this),
            });
        }

        /**
         * @private
         * @returns {integer}
         */
        _computeLocalMessageUnreadCounter() {
            if (this.model !== 'discuss.channel') {
                // unread counter only makes sense on channels
                return clear();
            }
            // By default trust the server up to the last message it used
            // because it's not possible to do better.
            let baseCounter = this.serverMessageUnreadCounter;
            let countFromId = this.serverLastMessage ? this.serverLastMessage.id : 0;
            // But if the client knows the last seen message that the server
            // returned (and by assumption all the messages that come after),
            // the counter can be computed fully locally, ignoring potentially
            // obsolete values from the server.
            const firstMessage = this.orderedMessages[0];
            if (
                firstMessage &&
                this.lastSeenByCurrentPartnerMessageId &&
                this.lastSeenByCurrentPartnerMessageId >= firstMessage.id
            ) {
                baseCounter = 0;
                countFromId = this.lastSeenByCurrentPartnerMessageId;
            }
            // Include all the messages that are known locally but the server
            // didn't take into account.
            return this.orderedMessages.reduce((total, message) => {
                if (message.id <= countFromId) {
                    return total;
                }
                return total + 1;
            }, baseCounter);
        }

        /**
         * @private
         * @returns {discuss.messaging}
         */
        _computeMessaging() {
            return link(this.env.messaging);
        }

        /**
         * @private
         * @returns {discuss.channel.message[]}
         */
        _computeNeedactionMessages() {
            return replace(this.messages.filter(message => message.isNeedaction));
        }

        /**
         * @private
         * @returns {discuss.channel.message|undefined}
         */
        _computeMessageAfterNewMessageSeparator() {
            if (this.model !== 'discuss.channel') {
                return unlink();
            }
            if (this.localMessageUnreadCounter === 0) {
                return unlink();
            }
            const index = this.orderedMessages.findIndex(message =>
                message.id === this.lastSeenByCurrentPartnerMessageId
            );
            if (index === -1) {
                return unlink();
            }
            const message = this.orderedMessages[index + 1];
            if (!message) {
                return unlink();
            }
            return link(message);
        }

        /**
         * @private
         * @returns {discuss.channel.message[]}
         */
        _computeOrderedMessages() {
            return replace(this.messages.sort((m1, m2) => m1.id < m2.id ? -1 : 1));
        }

        /**
         * @private
         * @returns {res.partner[]}
         */
        _computeOrderedOtherTypingMembers() {
            return replace(this.orderedTypingMembers.filter(
                member => member !== this.env.messaging.currentPartner
            ));
        }

        /**
         * @private
         * @returns {res.partner[]}
         */
        _computeOrderedTypingMembers() {
            return [[
                'replace',
                this.orderedTypingMemberLocalIds
                    .map(localId => this.env.models['res.partner'].get(localId))
                    .filter(member => !!member),
            ]];
        }

        /**
         * @private
         * @returns {string}
         */
        _computeTypingStatusText() {
            if (this.orderedOtherTypingMembers.length === 0) {
                return this.constructor.fields.typingStatusText.default;
            }
            if (this.orderedOtherTypingMembers.length === 1) {
                return _.str.sprintf(
                    this.env._t("%s is typing..."),
                    this.orderedOtherTypingMembers[0].nameOrDisplayName
                );
            }
            if (this.orderedOtherTypingMembers.length === 2) {
                return _.str.sprintf(
                    this.env._t("%s and %s are typing..."),
                    this.orderedOtherTypingMembers[0].nameOrDisplayName,
                    this.orderedOtherTypingMembers[1].nameOrDisplayName
                );
            }
            return _.str.sprintf(
                this.env._t("%s, %s and more are typing..."),
                this.orderedOtherTypingMembers[0].nameOrDisplayName,
                this.orderedOtherTypingMembers[1].nameOrDisplayName
            );
        }

        /**
         * Compute an url string that can be used inside a href attribute
         *
         * @private
         * @returns {string}
         */
        _computeUrl() {
            const baseHref = this.env.session.url('/web');
            return `${baseHref}#action=discuss.action_discuss&active_id=${this.model}_${this.id}`;
        }

        /**
         * @private
         * @param {Object} param0
         * @param {boolean} param0.isTyping
         */
        async _notifyCurrentPartnerTypingStatus({ isTyping }) {
            if (
                this._forceNotifyNextCurrentPartnerTypingStatus ||
                isTyping !== this._currentPartnerLastNotifiedIsTyping
            ) {
                if (this.model === 'discuss.channel') {
                    await this.async(() => this.env.services.rpc({
                        model: 'discuss.channel',
                        method: 'notify_typing',
                        args: [this.id],
                        kwargs: { is_typing: isTyping },
                    }, { shadow: true }));
                }
                if (isTyping && this._currentPartnerLongTypingTimer.isRunning) {
                    this._currentPartnerLongTypingTimer.reset();
                }
            }
            this._forceNotifyNextCurrentPartnerTypingStatus = false;
            this._currentPartnerLastNotifiedIsTyping = isTyping;
        }

        /**
         * Cleans followers of current channel. In particular, chats are supposed
         * to work with "members", not with "followers". This clean up is only
         * necessary to remove illegitimate followers in stable version, it can
         * be removed in master after proper migration to clean the database.
         *
         * @private
         */
        _onChangeFollowersPartner() {
            if (this.channel_type !== 'chat') {
                return;
            }
            for (const follower of this.followers) {
                if (follower.partner) {
                    follower.remove();
                }
            }
        }

        /**
         * @private
         */
        _onChangeLastSeenByCurrentPartnerMessageId() {
            this.env.messagingBus.trigger('o-channel-last-seen-by-current-partner-message-id-changed', {
                channel: this,
            });
        }

        /**
         * @private
         */
        _onChangeChannelViews() {
            if (this.channelViews.length === 0) {
                return;
            }
            /**
             * Fetches followers of chats when they are displayed for the first
             * time. This is necessary to clean the followers.
             * @see `_onChangeFollowersPartner` for more information.
             */
            if (this.channel_type === 'chat' && !this.areFollowersLoaded) {
                this.refreshFollowers();
            }
        }

        /**
         * Handles change of pinned state coming from the server. Useful to
         * clear pending state once server acknowledged the change.
         *
         * @private
         * @see isPendingPinned
         */
        _onIsServerPinnedChanged() {
            if (this.isServerPinned === this.isPendingPinned) {
                this.update({ isPendingPinned: clear() });
            }
        }

        /**
         * Handles change of fold state coming from the server. Useful to
         * synchronize corresponding chat window.
         *
         * @private
         */
        _onServerFoldStateChanged() {
            if (!this.env.messaging.chatWindowManager) {
                // avoid crash during destroy
                return;
            }
            if (this.env.messaging.device.isMobile) {
                return;
            }
            if (this.serverFoldState === 'closed') {
                this.env.messaging.chatWindowManager.closeChannel(this, {
                    notifyServer: false,
                });
            } else {
                this.env.messaging.chatWindowManager.openChannel(this, {
                    isFolded: this.serverFoldState === 'folded',
                    notifyServer: false,
                });
            }
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * @private
         */
        async _onCurrentPartnerInactiveTypingTimeout() {
            await this.async(() => this.unregisterCurrentPartnerIsTyping());
        }

        /**
         * Called when current partner has been typing for a very long time.
         * Immediately notify other members that he/she is still typing.
         *
         * @private
         */
        async _onCurrentPartnerLongTypingTimeout() {
            this._forceNotifyNextCurrentPartnerTypingStatus = true;
            this._throttleNotifyCurrentPartnerTypingStatus.clear();
            await this.async(
                () => this._throttleNotifyCurrentPartnerTypingStatus({ isTyping: true })
            );
        }

        /**
         * @private
         * @param {res.partner} partner
         */
        async _onOtherMemberLongTypingTimeout(partner) {
            if (!this.typingMembers.includes(partner)) {
                this._otherMembersLongTypingTimers.delete(partner);
                return;
            }
            this.unregisterOtherMemberTypingMember(partner);
        }

    }

    DiscussChannel.fields = {
        caches: one2many('discuss.channel_cache', {
            inverse: 'channel',
            isCausal: true,
        }),
        channel_type: attr(),
        /**
         * States the `discuss.chat_window` related to `this`. Serves as compute
         * dependency. It is computed from the inverse relation and it should
         * otherwise be considered read-only.
         */
        chatWindow: one2one('discuss.chat_window', {
            inverse: 'channel',
        }),
        /**
         * Serves as compute dependency.
         */
        chatWindowIsFolded: attr({
            related: 'chatWindow.isFolded',
        }),
        composer: one2one('discuss.channel.message_composer', {
            default: create(),
            inverse: 'channel',
            isCausal: true,
            readonly: true,
        }),
        correspondent: many2one('res.partner', {
            compute: '_computeCorrespondent',
            dependencies: [
                'channel_type',
                'members',
                'messagingCurrentPartner',
            ],
        }),
        correspondentNameOrDisplayName: attr({
            related: 'correspondent.nameOrDisplayName',
        }),
        counter: attr({
            default: 0,
        }),
        creator: many2one('res.users'),
        custom_channel_name: attr(),
        displayName: attr({
            compute: '_computeDisplayName',
            dependencies: [
                'channel_type',
                'correspondent',
                'correspondentNameOrDisplayName',
                'custom_channel_name',
                'name',
            ],
        }),
        /**
         * Determine whether this channel has the seen indicators (V and VV)
         * enabled or not.
         */
        hasSeenIndicators: attr({
            compute: '_computeHasSeenIndicators',
            default: false,
            dependencies: [
                'channel_type',
            ],
        }),
        id: attr({
            required: true,
        }),
        /**
         * States whether this channel is a `discuss.channel` qualified as chat.
         *
         * Useful to list chat channels, like in messaging menu with the filter
         * 'chat'.
         */
        isChatChannel: attr({
            compute: '_computeIsChatChannel',
            dependencies: [
                'channel_type',
            ],
            default: false,
        }),
        /**
         * Determine if there is a pending pin state change, which is a change
         * of pin state requested by the client but not yet confirmed by the
         * server.
         *
         * This field can be updated to immediately change the pin state on the
         * interface and to notify the server of the new state.
         */
        isPendingPinned: attr(),
        /**
         * Boolean that determines whether this channel is pinned
         * in discuss and present in the messaging menu.
         */
        isPinned: attr({
            compute: '_computeIsPinned',
            dependencies: [
                'isPendingPinned',
                'isServerPinned',
            ],
        }),
        /**
         * Determine the last pin state known by the server, which is the pin
         * state displayed after initialization or when the last pending
         * pin state change was confirmed by the server.
         *
         * This field should be considered read only in most situations. Only
         * the code handling pin state change from the server should typically
         * update it.
         */
        isServerPinned: attr({
            default: false,
        }),
        lastCurrentPartnerMessageSeenByEveryone: many2one('discuss.channel.message', {
            compute: '_computeLastCurrentPartnerMessageSeenByEveryone',
            dependencies: [
                'messagingCurrentPartner',
                'orderedMessages',
                'partnerSeenInfos',
            ],
        }),
        /**
         * Last message of the channel.
         */
        lastMessage: many2one('discuss.channel.message', {
            compute: '_computeLastMessage',
            dependencies: ['orderedMessages'],
        }),
        /**
         * States the last known needaction message of this channel.
         */
        lastNeedactionMessage: many2one('discuss.channel.message', {
            compute: '_computeLastNeedactionMessage',
            dependencies: [
                'needactionMessages',
            ],
        }),
        /**
         * Last seen message id of the channel by current partner.
         *
         * Also, it needs to be kept as an id because it's considered like a "date" and could stay
         * even if corresponding message is deleted. It is basically used to know which
         * messages are before or after it.
         */
        lastSeenByCurrentPartnerMessageId: attr({
            compute: '_computeLastSeenByCurrentPartnerMessageId',
            default: 0,
            dependencies: [
                'lastSeenByCurrentPartnerMessageId',
                'messagingCurrentPartner',
                'orderedMessages',
                // FIXME missing dependency 'orderedMessages.author', (task-2261221)
            ],
        }),
        /**
         * Local value of message unread counter, that means it is based on initial server value and
         * updated with interface updates.
         */
        localMessageUnreadCounter: attr({
            compute: '_computeLocalMessageUnreadCounter',
            dependencies: [
                'lastSeenByCurrentPartnerMessageId',
                'messagingCurrentPartner',
                'orderedMessages',
                'serverLastMessage',
                'serverMessageUnreadCounter',
            ],
        }),
        mainCache: one2one('discuss.channel_cache', {
            compute: '_computeMainCache',
        }),
        members: many2many('res.partner'),
        /**
         * Determines the message before which the "new message" separator must
         * be positioned, if any.
         */
        messageAfterNewMessageSeparator: many2one('discuss.channel.message', {
            compute: '_computeMessageAfterNewMessageSeparator',
            dependencies: [
                'lastSeenByCurrentPartnerMessageId',
                'localMessageUnreadCounter',
                'orderedMessages',
            ],
        }),
        message_needaction_counter: attr({
            default: 0,
        }),
        /**
         * All messages that this channel is linked to.
         */
        messages: one2many('discuss.channel.message', {
            inverse: 'channel',
            readonly: true,
        }),
        /**
         * Contains the message fetched/seen indicators for all messages of this channel.
         * FIXME This field should be readonly once task-2336946 is done.
         */
        messageSeenIndicators: one2many('discuss.message_seen_indicator', {
            inverse: 'channel',
            isCausal: true,
        }),
        /**
         * States the current messaging instance. Not useful by itself because
         * messaging is already in the env. But this allows the inverse relation
         * to contain all known channels. It also serves as compute dependency.
         */
        messaging: many2one('discuss.messaging', {
            compute: '_computeMessaging',
            inverse: 'allChannels',
        }),
        messagingCurrentPartner: many2one('res.partner', {
            related: 'messaging.currentPartner',
        }),
        name: attr(),
        /**
         * States all known needaction messages having of this channel.
         */
        needactionMessages: many2many('discuss.channel.message', {
            compute: '_computeNeedactionMessages',
            dependencies: [
                'messages',
            ],
        }),
        /**
         * Not a real field, used to trigger `_onChangeLastSeenByCurrentPartnerMessageId` when one of
         * the dependencies changes.
         */
        onChangeLastSeenByCurrentPartnerMessageId: attr({
            compute: '_onChangeLastSeenByCurrentPartnerMessageId',
            dependencies: [
                'lastSeenByCurrentPartnerMessageId',
            ],
            isOnChange: true,
        }),
        /**
         * Not a real field, used to trigger `_onChangeChannelViews` when one of
         * the dependencies changes.
         */
        onChangeChannelView: attr({
            compute: '_onChangeChannelViews',
            dependencies: [
                'channelViews',
            ],
            isOnChange: true,
        }),
        /**
         * Not a real field, used to trigger `_onIsServerPinnedChanged` when one of
         * the dependencies changes.
         */
        onIsServerPinnedChanged: attr({
            compute: '_onIsServerPinnedChanged',
            dependencies: [
                'isServerPinned',
            ],
            isOnChange: true,
        }),
        /**
         * Not a real field, used to trigger `_onServerFoldStateChanged` when one of
         * the dependencies changes.
         */
        onServerFoldStateChanged: attr({
            compute: '_onServerFoldStateChanged',
            dependencies: [
                'serverFoldState',
            ],
            isOnChange: true,
        }),
        /**
         * All messages ordered like they are displayed.
         */
        orderedMessages: many2many('discuss.channel.message', {
            compute: '_computeOrderedMessages',
            dependencies: ['messages'],
        }),
        /**
         * Ordered typing members on this channel, excluding the current partner.
         */
        orderedOtherTypingMembers: many2many('res.partner', {
            compute: '_computeOrderedOtherTypingMembers',
            dependencies: ['orderedTypingMembers'],
        }),
        /**
         * Ordered typing members on this channel. Lower index means this member
         * is currently typing for the longest time. This list includes current
         * partner as typer.
         */
        orderedTypingMembers: many2many('res.partner', {
            compute: '_computeOrderedTypingMembers',
            dependencies: [
                'orderedTypingMemberLocalIds',
                'typingMembers',
            ],
        }),
        /**
         * Technical attribute to manage ordered list of typing members.
         */
        orderedTypingMemberLocalIds: attr({
            default: [],
        }),
        /**
         * Contains the seen information for all members of the channel.
         * FIXME This field should be readonly once task-2336946 is done.
         */
        partnerSeenInfos: one2many('discuss.channel_partner_seen_info', {
            inverse: 'channel',
            isCausal: true,
        }),
        /**
         * Determine if there is a pending seen message change, which is a change
         * of seen message requested by the client but not yet confirmed by the
         * server.
         */
        pendingSeenMessageId: attr(),
        /**
         * Determine the last fold state known by the server, which is the fold
         * state displayed after initialization or when the last pending
         * fold state change was confirmed by the server.
         *
         * This field should be considered read only in most situations. Only
         * the code handling fold state change from the server should typically
         * update it.
         */
        serverFoldState: attr({
            default: 'closed',
        }),
        /**
         * Last message considered by the server.
         *
         * Useful to compute localMessageUnreadCounter field.
         *
         * @see localMessageUnreadCounter
         */
        serverLastMessage: many2one('discuss.channel.message'),
        /**
         * Message unread counter coming from server.
         *
         * Value of this field is unreliable, due to dynamic nature of
         * messaging. So likely outdated/unsync with server. Should use
         * localMessageUnreadCounter instead, which smartly guess the actual
         * message unread counter at all time.
         *
         * @see localMessageUnreadCounter
         */
        serverMessageUnreadCounter: attr({
            default: 0,
        }),
        channelViews: one2many('discuss.channel_view', {
            inverse: 'channel',
        }),
        /**
         * Members that are currently typing something in the composer of this
         * channel, including current partner.
         */
        typingMembers: many2many('res.partner'),
        /**
         * Text that represents the status on this channel about typing members.
         */
        typingStatusText: attr({
            compute: '_computeTypingStatusText',
            default: '',
            dependencies: ['orderedOtherTypingMembers'],
        }),
        /**
         * URL to access to the conversation.
         */
        url: attr({
            compute: '_computeUrl',
            default: '',
            dependencies: [
                'id',
            ]
        }),
        uuid: attr(),
    };

    DiscussChannel.modelName = 'discuss.channel';

    return DiscussChannel;
}

registerNewModel('discuss.channel', factory);
