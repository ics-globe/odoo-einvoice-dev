/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelMemberListCategoryView',
    identifyingFields: [['channelMemberListViewOwnerAsOffline', 'channelMemberListViewOwnerAsOnline']],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeMembers() {
            if (!this.exists()) {
                return clear();
            }
            if (this.channelMemberListViewOwnerAsOnline) {
                return replace(this.channelMemberListViewOwnerAsOnline.channel.orderedOnlineMembers);
            }
            if (this.channelMemberListViewOwnerAsOffline) {
                return replace(this.channelMemberListViewOwnerAsOffline.channel.orderedOfflineMembers);
            }
            return clear();
        },
    },
    fields: {
        channelMemberListViewOwnerAsOffline: one('ChannelMemberListView', {
            inverse: 'offlineCategoryView',
            readonly: true,
        }),
        channelMemberListViewOwnerAsOnline: one('ChannelMemberListView', {
            inverse: 'onlineCategoryView',
            readonly: true,
        }),
        members: many('Partner', {
            compute: '_computeMembers',
        }),
    },
});
