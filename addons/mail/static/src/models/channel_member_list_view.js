/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, replace, insert, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ChannelMemberListView',
    identifyingFields: [['chatWindowOwner', 'threadViewOwner']],
    lifecycleHooks: {
        _created() {
            this.fetchChannelMembers();
        }
    },
    recordMethods: {
        /**
         * Handles click on the "load more members" button.
         */
        async onClickLoadMoreMembers() {
            this.fetchChannelMembers();
        },
        async fetchChannelMembers() {
            const channelPartnersList = await this.messaging.rpc({
                model: 'mail.channel',
                method: 'load_more_members',
                args: [[this.channel.id]],
                kwargs: {
                    'known_member_ids': this.channel.channelPartners.map(channelPartner => channelPartner.partner.id),
                },
            });
            for (const partner of channelPartnersList) {
                const relation = { channel: replace(this.channel) };
                relation.partner = insert(partner);
                this.channel.update({ channelPartners: insertAndReplace(relation) });
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChannel() {
            if (this.chatWindowOwner) {
                return replace(this.chatWindowOwner.thread.channelOwner);
            }
            if (this.threadViewOwner) {
                return replace(this.threadViewOwner.thread.channelOwner);
            }
            return clear();
        },
    },
    fields: {
        channel: one('Channel', {
            compute: '_computeChannel',
            readonly: true,
        }),
        component: attr(),
        chatWindowOwner: one('ChatWindow', {
            inverse: 'channelMemberListView',
            readonly: true,
        }),
        threadViewOwner: one('ThreadView', {
            inverse: 'channelMemberListView',
            readonly: true,
        }),
    },
});
