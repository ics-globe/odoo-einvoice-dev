/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2one } from '@mail/model/model_field';
import { link } from '@mail/model/model_field_command';

function factory(dependencies) {
    class CategoryItem extends dependencies['mail.model'] {

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @override
         */
         static _createRecordLocalId(data) {
            return `${this.modelName}_${data.threadId}`;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeAvatarUrl() {
            switch (this.type) {
                case 'channel':
                    return `/web/image/mail.channel/${this.threadId}/image_128`;
                case 'chat':
                    return this.correspondentAvatarUrl;
                default:
                    return '/mail/static/src/img/smiley/avatar.jpg';
            }
        }

        /**
         * @private
         * @returns {integer}
         */
        _computerCounter() {
            switch (this.type) {
                case 'channel':
                    return this.threadMessageNeedactionCounter;
                case 'chat':
                    return this.threadLocalMessageUnreadCounter;
                default:
                    return 0;
            }
        }

        /**
         * @private
         * @returns {mail.discuss}
         */
        _computeDiscuss() {
            return link(this.env.messaging.discuss);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasLeave() {
            return this.type === 'channel' &&
                !this.threadMessageNeedactionCounter &&
                !this.threadGroupBasedSubscription
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasRename() {
            return this.type === 'chat';
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasSettings() {
            return this.type === 'channel';
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasUnpin() {
            return this.type === 'chat' && !this.threadLocalMessageUnreadCounter;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsActive() {
            return this.thread === this.discussThread;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsRenaming() {
            return this.hasRename && this.discussRenamingThreads.includes(this.thread);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsUnread() {
            return this.threadLocalMessageUnreadCounter > 0;
        }

        /**
         * @private
         * @returns {mail.thread}
         */
        _computeThread() {
            return link(this.env.models['mail.thread'].findFromIdentifyingData({
                id: this.threadId,
                model: 'mail.channel',
            }));
        }

    }

    CategoryItem.fields = {
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
            dependencies: [
                'type',
                'correspondentAvatarUrl',
                'threadId',
            ],
        }),
        /**
         * Correspondent of the related thread.
         * Serves as compute dependency.
         */
        correspondent: many2one('mail.partner', {
            related: 'thread.correspondent',
        }),
        /**
         * Serves as compute dependency.
         */
        correspondentAvatarUrl: attr({
            related: 'correspondent.avatarUrl',
        }),
        /**
         * Amount of unread/action-needed messages
         */
        counter: attr({
            compute: '_computerCounter',
            dependencies: [
                'type',
                'threadLocalMessageUnreadCounter',
                'threadMessageNeedactionCounter',
            ]
        }),
        displayName: attr({
            related: 'thread.displayName',
        }),
        discuss: many2one('mail.discuss', {
            compute: '_computeDiscuss',
        }),
        /**
         * Serves as compute dependency.
         */
        discussRenamingThreads: many2many('mail.thread', {
            related: 'discuss.renamingThreads',
        }),
        /**
         * Serves as compute dependency.
         */
        discussThread: many2one('mail.thread', {
            related: 'discuss.thread',
        }),
        /**
         * Boolean determines whether the item has a "leave" command
         */
        hasLeave: attr({
            compute: '_computeHasLeave',
            dependencies: [
                'type',
                'threadGroupBasedSubscription',
                'threadMessageNeedactionCounter',
            ],
        }),
        /**
         * Boolean determines whether the item has a "rename" command
         */
        hasRename: attr({
            compute: '_computeHasRename',
            dependencies: ['type'],
        }),
        /**
         * Boolean determines whether the item has a "settings" command
         */
        hasSettings: attr({
            compute: '_computeHasSettings',
            dependencies: ['type'],
        }),
        /**
         * Boolean determines whether the item has a "unpin" command
         */
        hasUnpin: attr({
            compute: '_computeHasUnpin',
            dependencies: [
                'type',
                'threadLocalMessageUnreadCounter',
            ],
        }),
        isActive: attr({
            compute: '_computeIsActive',
            dependencies: [
                'discussThread',
                'thread',
            ],
        }),
        isRenaming: attr({
            compute: '_computeIsRenaming',
            dependencies: [
                'discussRenamingThreads',
                'hasRename',
                'thread',
            ],
        }),
        isUnread: attr({
            compute: '_computeIsUnread',
            dependencies: ['threadLocalMessageUnreadCounter'],
        }),
        thread: one2one('mail.thread', {
            compute: '_computeThread',
            dependencies: ['threadId'],
        }),
        /**
         * Serves as compute dependency.
         */
        threadGroupBasedSubscription: attr({
            related: 'thread.group_based_subscription',
        }),
        threadId: attr({
            required: true,
        }),
        /**
         * Serves as compute dependency.
         */
        threadLocalMessageUnreadCounter: attr({
            related: 'thread.localMessageUnreadCounter',
        }),
        threadMassMailing: attr({
            related: 'thread.mass_mailing',
        }),
        /**
         * Serves as compute dependency.
         */
        threadMessageNeedactionCounter: attr({
            related: 'thread.message_needaction_counter',
        }),
        threadName: attr({
            related: 'thread.name',
        }),
        type: attr({
            related: 'thread.channel_type',
        })
    };

    CategoryItem.modelName = 'mail.category_item';

    return CategoryItem;
}

registerNewModel('mail.category_item', factory);
