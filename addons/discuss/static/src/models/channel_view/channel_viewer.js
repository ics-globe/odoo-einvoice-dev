/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr, many2one, one2one } from '@discuss/model/model_field';
import { create, insert, link, unlink } from '@discuss/model/model_field_command';

function factory(dependencies) {

    class DiscussChannelViewer extends dependencies['discuss.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {integer} scrollHeight
         * @param {discuss.channel_cache} channelCache
         */
        saveChannelCacheScrollHeightAsInitial(scrollHeight, channelCache) {
            channelCache = channelCache || this.channelCache;
            if (!channelCache) {
                return;
            }
            if (this.chatter) {
                // Initial scroll height is disabled for chatter because it is
                // too complex to handle correctly and less important
                // functionally.
                return;
            }
            this.update({
                channelCacheInitialScrollHeights: Object.assign({}, this.channelCacheInitialScrollHeights, {
                    [channelCache.localId]: scrollHeight,
                }),
            });
        }

        /**
         * @param {integer} scrollTop
         * @param {discuss.channel_cache} channelCache
         */
        saveChannelCacheScrollPositionsAsInitial(scrollTop, channelCache) {
            channelCache = channelCache || this.channelCache;
            if (!channelCache) {
                return;
            }
            if (this.chatter) {
                // Initial scroll position is disabled for chatter because it is
                // too complex to handle correctly and less important
                // functionally.
                return;
            }
            this.update({
                channelCacheInitialScrollPositions: Object.assign({}, this.channelCacheInitialScrollPositions, {
                    [channelCache.localId]: scrollTop,
                }),
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {discuss.channel_cache|undefined}
         */
        _computeChannelCache() {
            if (!this.channel) {
                return unlink();
            }
            return insert({
                stringifiedDomain: this.stringifiedDomain,
                channel: link(this.channel),
            });
        }

        /**
         * @private
         * @returns {discuss.channel_viewer|undefined}
         */
        _computeChannelView() {
            if (!this.hasChannelView) {
                return unlink();
            }
            if (this.channelView) {
                return;
            }
            return create();
        }

    }

    DiscussChannelViewer.fields = {
        /**
         * Determines whether `this.channel` should be displayed.
         */
        hasChannelView: attr({
            default: false,
        }),
        /**
         * Determines the selected `discuss.channel_message`.
         */
        selectedMessage: many2one('discuss.channel_message'),
        /**
         * Determines the domain to apply when fetching messages for `this.channel`.
         */
        stringifiedDomain: attr({
            default: '[]',
        }),
        /**
         * Determines the `discuss.channel` that should be displayed by `this`.
         */
        channel: many2one('discuss.channel'),
        /**
         * States the `discuss.channel_cache` that should be displayed by `this`.
         */
        channelCache: many2one('discuss.channel_cache', {
            compute: '_computeChannelCache',
            dependencies: [
                'stringifiedDomain',
                'channel',
            ],
        }),
        /**
         * Determines the initial scroll height of channel caches, which is the
         * scroll height at the time the last scroll position was saved.
         * Useful to only restore scroll position when the corresponding height
         * is available, otherwise the restore makes no sense.
         */
        channelCacheInitialScrollHeights: attr({
            default: {},
        }),
        /**
         * Determines the initial scroll positions of channel caches.
         * Useful to restore scroll position on changing back to this
         * channel cache. Note that this is only applied when opening
         * the channel cache, because scroll position may change fast so
         * save is already throttled.
         */
        channelCacheInitialScrollPositions: attr({
            default: {},
        }),
        /**
         * States the `discuss.channel_view` currently displayed and managed by `this`.
         */
        channelView: one2one('discuss.channel_view', {
            compute: '_computeChannelView',
            dependencies: [
                'hasChannelView',
            ],
            inverse: 'channelViewer',
            isCausal: true,
        }),
    };

    DiscussChannelViewer.modelName = 'discuss.channel_viewer';

    return DiscussChannelViewer;
}

registerNewModel('discuss.channel_viewer', factory);
