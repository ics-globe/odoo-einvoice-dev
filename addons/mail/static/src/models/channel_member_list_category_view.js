/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'ChannelMemberListCategoryView',
    identifyingFields: [['channelMemberListViewOwnerAsOffline', 'channelMemberListViewOwnerAsOnline']],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannelMemberView() {
            if (this.members.length === 0) {
                return clear();
            }
            return replace(
                this.members.map(member => insertAndReplace({ partner: replace(member) })),
            );
        },
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
        /**
         * @private
         * @returns {string}
         */
        _computeTitle() {
            let categoryText = "";
            if (this.channelMemberListViewOwnerAsOnline) {
                categoryText = this.env._t("Online");
            }
            if (this.channelMemberListViewOwnerAsOffline) {
                categoryText = this.env._t("Offline");
            }
            return sprintf(
                this.env._t("%(categoryText)s - %(memberCount)s"),
                {
                    categoryText,
                    memberCount: this.members.length,
                }
            );
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
        channelMemberViews: many('ChannelMemberView', {
            compute: '_computeChannelMemberView',
            inverse: 'channelMemberListCategoryViewOwner',
            isCausal: true,
        }),
        members: many('Partner', {
            compute: '_computeMembers',
        }),
        title: attr({
            compute: '_computeTitle',
        }),
    },
});
