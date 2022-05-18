/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelMemberListView',
    identifyingFields: [['chatWindowOwner', 'threadViewOwner']],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannel() {
            if (this.chatWindowOwner) {
                return replace(this.chatWindowOwner.thread);
            }
            if (this.threadViewOwner) {
                return replace(this.threadViewOwner.thread);
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeOfflineCategoryView() {
            if (this.channel && this.channel.orderedOfflineMembers.length > 0) {
                return insertAndReplace();
            }
            return clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeOnlineCategoryView() {
            if (this.channel && this.channel.orderedOnlineMembers.length > 0) {
                return insertAndReplace();
            }
            return clear();
        },
    },
    fields: {
        channel: one('Thread', {
            compute: '_computeChannel',
            readonly: true,
        }),
        chatWindowOwner: one('ChatWindow', {
            inverse: 'channelMemberListView',
            readonly: true,
        }),
        offlineCategoryView: one('ChannelMemberListCategoryView', {
            compute: '_computeOfflineCategoryView',
            inverse: 'channelMemberListViewOwnerAsOffline',
            isCausal: true,
        }),
        onlineCategoryView: one('ChannelMemberListCategoryView', {
            compute: '_computeOnlineCategoryView',
            inverse: 'channelMemberListViewOwnerAsOnline',
            isCausal: true,
        }),
        threadViewOwner: one('ThreadView', {
            inverse: 'channelMemberListView',
            readonly: true,
        }),
    },
});
