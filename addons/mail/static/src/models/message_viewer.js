/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'MessageViewer',
    identifyingFields: [['messageListViewOwner', 'deleteMessageConfirmViewOwner']],
    recordMethods: {
        /**
         * @private
         * @returns {MessageView[]}
         */
        _computeMessageViews() {
            if (this.messageListViewOwner) {
                if (!this.messageListViewOwner.threadViewOwner.threadCache) {
                    return clear();
                }
                const orderedMessages = this.messageListViewOwner.threadViewOwner.threadCache.orderedNonEmptyMessages;
                if (this.messageListViewOwner.threadViewOwner.order === 'desc') {
                    orderedMessages.reverse();
                }
                const messageViewsData = [];
                let prevMessage;
                for (const message of orderedMessages) {
                    messageViewsData.push({
                        isSquashed: this.messageListViewOwner.threadViewOwner._shouldMessageBeSquashed(prevMessage, message),
                        message: replace(message),
                    });
                    prevMessage = message;
                }
                return insertAndReplace(messageViewsData);
            }
            if (this.deleteMessageConfirmViewOwner) {
                return this.deleteMessageConfirmViewOwner.message
                    ? insertAndReplace({ message: replace(this.deleteMessageConfirmViewOwner.message) })
                    : clear();
            }
            return clear();
        },
    },
    fields: {
        deleteMessageConfirmViewOwner: one('DeleteMessageConfirmView', {
            inverse: 'messageViewer',
            readonly: true,
        }),
        messageListViewOwner: one('MessageListView', {
            inverse: 'messageViewer',
            readonly: true,
        }),
        messageViews: many('MessageView', {
            compute: '_computeMessageViews',
            inverse: 'messageViewerOwner',
            isCausal: true,
        }),
    },
});
