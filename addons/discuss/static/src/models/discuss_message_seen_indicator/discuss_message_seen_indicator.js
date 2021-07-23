/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr, many2many, many2one, one2many } from '@discuss/model/model_field';
import { insert, replace, unlinkAll } from '@discuss/model/model_field_command';

function factory(dependencies) {

    class DiscussMessageSeenIndicator extends dependencies['discuss.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {discuss.channel} [channel] the concerned channel
         */
        static recomputeFetchedValues(channel = undefined) {
            const indicatorFindFunction = channel ? localIndicator => localIndicator.channel === channel : undefined;
            const indicators = this.env.models['discuss.message_seen_indicator'].all(indicatorFindFunction);
            for (const indicator of indicators) {
                indicator.update({
                    hasEveryoneFetched: indicator._computeHasEveryoneFetched(),
                    hasSomeoneFetched: indicator._computeHasSomeoneFetched(),
                    partnersThatHaveFetched: indicator._computePartnersThatHaveFetched(),
                });
            }
        }

        /**
         * @static
         * @param {discuss.channel} [channel] the concerned channel
         */
        static recomputeSeenValues(channel = undefined) {
            const indicatorFindFunction = channel ? localIndicator => localIndicator.channel === channel : undefined;
            const indicators = this.env.models['discuss.message_seen_indicator'].all(indicatorFindFunction);
            for (const indicator of indicators) {
                indicator.update({
                    hasEveryoneSeen: indicator._computeHasEveryoneSeen(),
                    hasSomeoneFetched: indicator._computeHasSomeoneFetched(),
                    hasSomeoneSeen: indicator._computeHasSomeoneSeen(),
                    isMessagePreviousToLastCurrentPartnerMessageSeenByEveryone:
                        indicator._computeIsMessagePreviousToLastCurrentPartnerMessageSeenByEveryone(),
                    partnersThatHaveFetched: indicator._computePartnersThatHaveFetched(),
                    partnersThatHaveSeen: indicator._computePartnersThatHaveSeen(),
                });
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            const { channelId, messageId } = data;
            return `${this.modelName}_${channelId}_${messageId}`;
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {boolean}
         * @see computeFetchedValues
         * @see computeSeenValues
         */
        _computeHasEveryoneFetched() {
            if (!this.message || !this.channel || !this.channel.partnerSeenInfos) {
                return false;
            }
            const otherPartnerSeenInfosDidNotFetch =
                this.channel.partnerSeenInfos.filter(partnerSeenInfo =>
                    partnerSeenInfo.partner !== this.message.author &&
                    (
                        !partnerSeenInfo.lastFetchedMessage ||
                        partnerSeenInfo.lastFetchedMessage.id < this.message.id
                    )
            );
            return otherPartnerSeenInfosDidNotFetch.length === 0;
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {boolean}
         * @see computeSeenValues
         */
        _computeHasEveryoneSeen() {
            if (!this.message || !this.channel || !this.channel.partnerSeenInfos) {
                return false;
            }
            const otherPartnerSeenInfosDidNotSee =
                this.channel.partnerSeenInfos.filter(partnerSeenInfo =>
                    partnerSeenInfo.partner !== this.message.author &&
                    (
                        !partnerSeenInfo.lastSeenMessage ||
                        partnerSeenInfo.lastSeenMessage.id < this.message.id
                    )
            );
            return otherPartnerSeenInfosDidNotSee.length === 0;
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {boolean}
         * @see computeFetchedValues
         * @see computeSeenValues
         */
        _computeHasSomeoneFetched() {
            if (!this.message || !this.channel || !this.channel.partnerSeenInfos) {
                return false;
            }
            const otherPartnerSeenInfosFetched =
                this.channel.partnerSeenInfos.filter(partnerSeenInfo =>
                    partnerSeenInfo.partner !== this.message.author &&
                    partnerSeenInfo.lastFetchedMessage &&
                    partnerSeenInfo.lastFetchedMessage.id >= this.message.id
            );
            return otherPartnerSeenInfosFetched.length > 0;
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {boolean}
         * @see computeSeenValues
         */
        _computeHasSomeoneSeen() {
            if (!this.message || !this.channel || !this.channel.partnerSeenInfos) {
                return false;
            }
            const otherPartnerSeenInfosSeen =
                this.channel.partnerSeenInfos.filter(partnerSeenInfo =>
                    partnerSeenInfo.partner !== this.message.author &&
                    partnerSeenInfo.lastSeenMessage &&
                    partnerSeenInfo.lastSeenMessage.id >= this.message.id
            );
            return otherPartnerSeenInfosSeen.length > 0;
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {boolean}
         * @see computeSeenValues
         */
        _computeIsMessagePreviousToLastCurrentPartnerMessageSeenByEveryone() {
            if (
                !this.message ||
                !this.channel ||
                !this.channel.lastCurrentPartnerMessageSeenByEveryone
            ) {
                return false;
            }
            return this.message.id < this.channel.lastCurrentPartnerMessageSeenByEveryone.id;
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {res.partner[]}
         * @see computeFetchedValues
         * @see computeSeenValues
         */
        _computePartnersThatHaveFetched() {
            if (!this.message || !this.channel || !this.channel.partnerSeenInfos) {
                return unlinkAll();
            }
            const otherPartnersThatHaveFetched = this.channel.partnerSeenInfos
                .filter(partnerSeenInfo =>
                    /**
                     * Relation may not be set yet immediately
                     * @see discuss.channel_partner_seen_info:partnerId field
                     * FIXME task-2278551
                     */
                    partnerSeenInfo.partner &&
                    partnerSeenInfo.partner !== this.message.author &&
                    partnerSeenInfo.lastFetchedMessage &&
                    partnerSeenInfo.lastFetchedMessage.id >= this.message.id
                )
                .map(partnerSeenInfo => partnerSeenInfo.partner);
            if (otherPartnersThatHaveFetched.length === 0) {
                return unlinkAll();
            }
            return replace(otherPartnersThatHaveFetched);
        }

        /**
         * Manually called as not always called when necessary
         *
         * @private
         * @returns {res.partner[]}
         * @see computeSeenValues
         */
        _computePartnersThatHaveSeen() {
            if (!this.message || !this.channel || !this.channel.partnerSeenInfos) {
                return unlinkAll();
            }
            const otherPartnersThatHaveSeen = this.channel.partnerSeenInfos
                .filter(partnerSeenInfo =>
                    /**
                     * Relation may not be set yet immediately
                     * @see discuss.channel_partner_seen_info:partnerId field
                     * FIXME task-2278551
                     */
                    partnerSeenInfo.partner &&
                    partnerSeenInfo.partner !== this.message.author &&
                    partnerSeenInfo.lastSeenMessage &&
                    partnerSeenInfo.lastSeenMessage.id >= this.message.id)
                .map(partnerSeenInfo => partnerSeenInfo.partner);
            if (otherPartnersThatHaveSeen.length === 0) {
                return unlinkAll();
            }
            return replace(otherPartnersThatHaveSeen);
        }

        /**
         * @private
         * @returns {discuss.channel.message}
         */
        _computeMessage() {
            return insert({ id: this.messageId });
        }

        /**
         * @private
         * @returns {discuss.channel}
         */
        _computeThread() {
            return insert({
                id: this.channelId,
                model: 'discuss.channel',
            });
        }
    }

    DiscussMessageSeenIndicator.fields = {
        /**
         * The id of the channel this seen indicator is related to.
         *
         * Should write on this field to set relation between the channel and
         * this seen indicator, not on `channel`.
         *
         * Reason for not setting the relation directly is the necessity to
         * uniquely identify a seen indicator based on channel and message from data.
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
        hasEveryoneFetched: attr({
            compute: '_computeHasEveryoneFetched',
            default: false,
            dependencies: ['messageAuthor', 'messageId', 'channelPartnerSeenInfos'],
        }),
        hasEveryoneSeen: attr({
            compute: '_computeHasEveryoneSeen',
            default: false,
            dependencies: ['messageAuthor', 'messageId', 'channelPartnerSeenInfos'],
        }),
        hasSomeoneFetched: attr({
            compute: '_computeHasSomeoneFetched',
            default: false,
            dependencies: ['messageAuthor', 'messageId', 'channelPartnerSeenInfos'],
        }),
        hasSomeoneSeen: attr({
            compute: '_computeHasSomeoneSeen',
            default: false,
            dependencies: ['messageAuthor', 'messageId', 'channelPartnerSeenInfos'],
        }),
        id: attr(),
        isMessagePreviousToLastCurrentPartnerMessageSeenByEveryone: attr({
            compute: '_computeIsMessagePreviousToLastCurrentPartnerMessageSeenByEveryone',
            default: false,
            dependencies: [
                'messageId',
                'channelLastCurrentPartnerMessageSeenByEveryone',
            ],
        }),
        /**
         * The message concerned by this seen indicator.
         * This is automatically computed based on messageId field.
         * @see messageId
         */
        message: many2one('discuss.channel.message', {
            compute: '_computeMessage',
            dependencies: [
                'messageId',
            ],
        }),
        messageAuthor: many2one('res.partner', {
            related: 'message.author',
        }),
        /**
         * The id of the message this seen indicator is related to.
         *
         * Should write on this field to set relation between the channel and
         * this seen indicator, not on `message`.
         *
         * Reason for not setting the relation directly is the necessity to
         * uniquely identify a seen indicator based on channel and message from data.
         * Relational data are list of commands, which is problematic to deduce
         * identifying records.
         *
         * TODO: task-2322536 (normalize relational data) & task-2323665
         * (required fields) should improve and let us just use the relational
         * fields.
         */
        messageId: attr({
            required: true,
        }),
        partnersThatHaveFetched: many2many('res.partner', {
            compute: '_computePartnersThatHaveFetched',
            dependencies: ['messageAuthor', 'messageId', 'channelPartnerSeenInfos'],
        }),
        partnersThatHaveSeen: many2many('res.partner', {
            compute: '_computePartnersThatHaveSeen',
            dependencies: ['messageAuthor', 'messageId', 'channelPartnerSeenInfos'],
        }),
        /**
         * The channel concerned by this seen indicator.
         * This is automatically computed based on channelId field.
         * @see channelId
         */
        channel: many2one('discuss.channel', {
            compute: '_computeThread',
            dependencies: [
                'channelId',
            ],
            inverse: 'messageSeenIndicators'
        }),
        channelPartnerSeenInfos: one2many('discuss.channel_partner_seen_info', {
            related: 'channel.partnerSeenInfos',
        }),
        channelLastCurrentPartnerMessageSeenByEveryone: many2one('discuss.channel.message', {
            related: 'channel.lastCurrentPartnerMessageSeenByEveryone',
        }),
    };

    DiscussMessageSeenIndicator.modelName = 'discuss.message_seen_indicator';

    return DiscussMessageSeenIndicator;
}

registerNewModel('discuss.message_seen_indicator', factory);
