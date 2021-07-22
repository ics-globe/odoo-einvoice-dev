/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr, many2one } from '@discuss/model/model_field';
import { insert } from '@discuss/model/model_field_command';

function factory(dependencies) {

    class DiscussChannelPartnerSeenInfo extends dependencies['discuss.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            const { channelId, partnerId } = data;
            return `${this.modelName}_${channelId}_${partnerId}`;
        }

        /**
         * @private
         * @returns {res.partner|undefined}
         */
        _computePartner() {
            return insert({ id: this.partnerId });
        }

        /**
         * @private
         * @returns {discuss.channel|undefined}
         */
        _computeChannel() {
            return insert({ id: this.channelId });
        }

    }

    DiscussChannelPartnerSeenInfo.modelName = 'discuss.channel_partner_seen_info';

    DiscussChannelPartnerSeenInfo.fields = {
        /**
         * The id of channel this seen info is related to.
         *
         * Should write on this field to set relation between the channel and
         * this seen info, not on `channel`.
         *
         * Reason for not setting the relation directly is the necessity to
         * uniquely identify a seen info based on channel and partner from data.
         * Relational data are list of commands, which is problematic to deduce
         * identifying records.
         *
         * TODO: task-2322536 (normalize relational data) & task-2323665
         * (required fields) should improve and let us just use the relational
         * fields.
         */
        channelId: attr({
            required: true,
        }),
        lastFetchedMessage: many2one('discuss.channel_message'),
        lastSeenMessage: many2one('discuss.channel_message'),
        /**
         * Partner that this seen info is related to.
         *
         * Should not write on this field to update relation, and instead
         * should write on @see partnerId field.
         */
        partner: many2one('res.partner', {
            compute: '_computePartner',
            dependencies: ['partnerId'],
        }),
        /**
         * The id of partner this seen info is related to.
         *
         * Should write on this field to set relation between the partner and
         * this seen info, not on `partner`.
         *
         * Reason for not setting the relation directly is the necessity to
         * uniquely identify a seen info based on channel and partner from data.
         * Relational data are list of commands, which is problematic to deduce
         * identifying records.
         *
         * TODO: task-2322536 (normalize relational data) & task-2323665
         * (required fields) should improve and let us just use the relational
         * fields.
         */
        partnerId: attr({
            required: true,
        }),
        /**
         * Channel that this seen info is related to.
         *
         * Should not write on this field to update relation, and instead
         * should write on @see channelId field.
         */
        channel: many2one('discuss.channel', {
            compute: '_computeChannel',
            dependencies: ['channelId'],
            inverse: 'partnerSeenInfos',
        }),
    };

    return DiscussChannelPartnerSeenInfo;
}

registerNewModel('discuss.channel_partner_seen_info', factory);
