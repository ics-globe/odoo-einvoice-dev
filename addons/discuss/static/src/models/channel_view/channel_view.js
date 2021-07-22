/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { RecordDeletedError } from '@discuss/model/model_errors';
import { attr, many2many, many2one, one2one } from '@discuss/model/model_field';
import { clear, link, unlink } from '@discuss/model/model_field_command';

function factory(dependencies) {

    class DiscussChannelView extends dependencies['discuss.model'] {

        /**
         * @override
         */
        _willDelete() {
            this.env.browser.clearTimeout(this._loaderTimeout);
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * This function register a hint for the component related to this
         * record. Hints are information on changes around this viewer that
         * make require adjustment on the component. For instance, if this
         * channel view initiated a channel cache load and it now has become
         * loaded, then it may need to auto-scroll to last message.
         *
         * @param {string} hintType name of the hint. Used to determine what's
         *   the broad type of adjustement the component has to do.
         * @param {any} [hintData] data of the hint. Used to fine-tune
         *   adjustments on the component.
         */
        addComponentHint(hintType, hintData) {
            const hint = { data: hintData, type: hintType };
            this.update({
                componentHintList: this.componentHintList.concat([hint]),
            });
        }

        /**
         * @param {Object} hint
         */
        markComponentHintProcessed(hint) {
            this.update({
                componentHintList: this.componentHintList.filter(h => h !== hint),
            });
            this.env.messagingBus.trigger('o-channel-view-hint-processed', {
                hint,
                channelViewer: this.channelViewer,
            });
        }

        /**
         * @param {discuss.channel_message} message
         */
        handleVisibleMessage(message) {
            if (!this.lastVisibleMessage || this.lastVisibleMessage.id < message.id) {
                this.update({ lastVisibleMessage: link(message) });
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {discuss.messaging}
         */
        _computeMessaging() {
            return link(this.env.messaging);
        }

        /**
         * @private
         * @returns {string[]}
         */
        _computeTextInputSendShortcuts() {
            // Actually in mobile there is a send button, so we need 'enter' to allow new line.
            // Hence, we want to use a different shortcut 'ctrl/meta enter' to send.
            if (this.env.messaging.device.isMobile) {
                return ['ctrl-enter', 'meta-enter'];
            }
            return ['enter'];
        }

        /**
         * @private
         * @returns {integer|undefined}
         */
        _computeChannelCacheInitialScrollHeight() {
            if (!this.channelCache) {
                return clear();
            }
            const channelCacheInitialScrollHeight = this.channelCacheInitialScrollHeights[this.channelCache.localId];
            if (channelCacheInitialScrollHeight !== undefined) {
                return channelCacheInitialScrollHeight;
            }
            return clear();
        }

        /**
         * @private
         * @returns {integer|undefined}
         */
        _computeChannelCacheInitialScrollPosition() {
            if (!this.channelCache) {
                return clear();
            }
            const channelCacheInitialScrollPosition = this.channelCacheInitialScrollPositions[this.channelCache.localId];
            if (channelCacheInitialScrollPosition !== undefined) {
                return channelCacheInitialScrollPosition;
            }
            return clear();
        }

        /**
         * Not a real field, used to trigger `channel.markAsSeen` when one of
         * the dependencies changes.
         *
         * @private
         * @returns {boolean}
         */
        _computeChannelShouldBeSetAsSeen() {
            if (!this.channel) {
                return;
            }
            if (!this.channel.lastMessage) {
                return;
            }
            if (!this.lastVisibleMessage) {
                return;
            }
            if (this.lastVisibleMessage !== this.lastMessage) {
                return;
            }
            if (!this.hasComposerFocus) {
                // FIXME condition should not be on "composer is focused" but "channel view is active"
                // See task-2277543
                return;
            }
            this.channel.markAsSeen(this.channel.lastMessage).catch(e => {
                // prevent crash when executing compute during destroy
                if (!(e instanceof RecordDeletedError)) {
                    throw e;
                }
            });
        }

        /**
         * @private
         */
        _onChannelCacheChanged() {
            // clear obsolete hints
            this.update({ componentHintList: clear() });
            this.addComponentHint('change-of-channel-cache');
            if (this.channelCache) {
                this.channelCache.update({
                    isCacheRefreshRequested: true,
                    isMarkAllAsReadRequested: true,
                });
            }
            this.update({ lastVisibleMessage: unlink() });
        }

        /**
         * @private
         */
        _onChannelCacheIsLoadingChanged() {
            if (this.channelCache && this.channelCache.isLoading) {
                if (!this.isLoading && !this.isPreparingLoading) {
                    this.update({ isPreparingLoading: true });
                    this.async(() =>
                        new Promise(resolve => {
                            this._loaderTimeout = this.env.browser.setTimeout(resolve, 400);
                        }
                    )).then(() => {
                        const isLoading = this.channelCache
                            ? this.channelCache.isLoading
                            : false;
                        this.update({ isLoading, isPreparingLoading: false });
                    });
                }
                return;
            }
            this.env.browser.clearTimeout(this._loaderTimeout);
            this.update({ isLoading: false, isPreparingLoading: false });
        }
    }

    DiscussChannelView.fields = {
        /**
         * List of component hints. Hints contain information that help
         * components make UI/UX decisions based on their UI state.
         * For instance, on receiving new messages and the last message
         * is visible, it should auto-scroll to this new last message.
         *
         * Format of a component hint:
         *
         *   {
         *       type: {string} the name of the component hint. Useful
         *                      for components to dispatch behaviour
         *                      based on its type.
         *       data: {Object} data related to the component hint.
         *                      For instance, if hint suggests to scroll
         *                      to a certain message, data may contain
         *                      message id.
         *   }
         */
        componentHintList: attr({
            default: [],
        }),
        composer: many2one('discuss.channel_message_composer', {
            related: 'channel.composer',
        }),
        /**
         * Serves as compute dependency.
         */
        device: one2one('discuss.device', {
            related: 'messaging.device',
        }),
        /**
         * Serves as compute dependency.
         */
        deviceIsMobile: attr({
            related: 'device.isMobile',
        }),
        hasComposerFocus: attr({
            related: 'composer.hasFocus',
        }),
        /**
         * States whether `this.channelCache` is currently loading messages.
         *
         * This field is related to `this.channelCache.isLoading` but with a
         * delay on its update to avoid flickering on the UI.
         *
         * It is computed through `_onChannelCacheIsLoadingChanged` and it should
         * otherwise be considered read-only.
         */
        isLoading: attr({
            default: false,
        }),
        /**
         * States whether `this` is aware of `this.channelCache` currently
         * loading messages, but `this` is not yet ready to display that loading
         * on the UI.
         *
         * This field is computed through `_onChannelCacheIsLoadingChanged` and
         * it should otherwise be considered read-only.
         *
         * @see `this.isLoading`
         */
        isPreparingLoading: attr({
            default: false,
        }),
        /**
         * Determines whether `this` should automatically scroll on receiving
         * a new message. Detection of new message is done through the component
         * hint `message-received`.
         */
        hasAutoScrollOnMessageReceived: attr({
            default: true,
        }),
        /**
         * Last message in the context of the currently displayed channel cache.
         */
        lastMessage: many2one('discuss.channel_message', {
            related: 'channel.lastMessage',
        }),
        /**
         * Most recent message in this channel view that has been shown to the
         * current partner in the currently displayed channel cache.
         */
        lastVisibleMessage: many2one('discuss.channel_message'),
        messages: many2many('discuss.channel_message', {
            related: 'channelCache.messages',
        }),
        /**
         * Serves as compute dependency.
         */
        messaging: many2one('discuss.messaging', {
            compute: '_computeMessaging',
        }),
        nonEmptyMessages: many2many('discuss.channel_message', {
            related: 'channelCache.nonEmptyMessages',
        }),
        /**
         * Not a real field, used to trigger `_onChannelCacheChanged` when one of
         * the dependencies changes.
         */
        onChannelCacheChanged: attr({
            compute: '_onChannelCacheChanged',
            dependencies: [
                'channelCache'
            ],
            isOnChange: true,
        }),
        /**
         * Not a real field, used to trigger `_onChannelCacheIsLoadingChanged`
         * when one of the dependencies changes.
         *
         * @see `this.isLoading`
         */
        onChannelCacheIsLoadingChanged: attr({
            compute: '_onChannelCacheIsLoadingChanged',
            dependencies: [
                'channelCache',
                'channelCacheIsLoading',
            ],
            isOnChange: true,
        }),
        /**
         * Determines the domain to apply when fetching messages for `this.channel`.
         */
        stringifiedDomain: attr({
            related: 'channelViewer.stringifiedDomain',
        }),
        /**
         * Determines the keyboard shortcuts that are available to send a message
         * from the composer of this channel viewer.
         */
        textInputSendShortcuts: attr({
            compute: '_computeTextInputSendShortcuts',
            dependencies: [
                'device',
                'deviceIsMobile',
                'channel',
            ],
        }),
        /**
         * Determines the `discuss.channel` currently displayed by `this`.
         */
        channel: many2one('discuss.channel', {
            inverse: 'channelViews',
            readonly: true,
            related: 'channelViewer.channel',
        }),
        /**
         * States the `discuss.channel_cache` currently displayed by `this`.
         */
        channelCache: many2one('discuss.channel_cache', {
            inverse: 'channelViews',
            readonly: true,
            related: 'channelViewer.channelCache',
        }),
        channelCacheInitialScrollHeight: attr({
            compute: '_computeChannelCacheInitialScrollHeight',
            dependencies: [
                'channelCache',
                'channelCacheInitialScrollHeights',
            ],
        }),
        channelCacheInitialScrollPosition: attr({
            compute: '_computeChannelCacheInitialScrollPosition',
            dependencies: [
                'channelCache',
                'channelCacheInitialScrollPositions',
            ],
        }),
        /**
         * Serves as compute dependency.
         */
        channelCacheIsLoading: attr({
            related: 'channelCache.isLoading',
        }),
        /**
         * List of saved initial scroll heights of channel caches.
         */
        channelCacheInitialScrollHeights: attr({
            default: {},
            related: 'channelViewer.channelCacheInitialScrollHeights',
        }),
        /**
         * List of saved initial scroll positions of channel caches.
         */
        channelCacheInitialScrollPositions: attr({
            default: {},
            related: 'channelViewer.channelCacheInitialScrollPositions',
        }),
        /**
         * Not a real field, used to trigger `channel.markAsSeen` when one of
         * the dependencies changes.
         */
        channelShouldBeSetAsSeen: attr({
            compute: '_computeChannelShouldBeSetAsSeen',
            dependencies: [
                'hasComposerFocus',
                'lastMessage',
                'lastVisibleMessage',
                'channelCache',
            ],
            isOnChange: true,
        }),
        /**
         * Determines the `discuss.channel_viewer` currently managing `this`.
         */
        channelViewer: one2one('discuss.channel_viewer', {
            inverse: 'channelView',
            readonly: true,
        }),
    };

    DiscussChannelView.modelName = 'discuss.channel_view';

    return DiscussChannelView;
}

registerNewModel('discuss.channel_view', factory);
