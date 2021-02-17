/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentLinkPreviewView',
    identifyingFields: ['attachmentList', 'attachment'],
    recordMethods: {
        /**
         * Handles the click on delete attachment and open the confirm dialog.
         *
         * @param {MouseEvent} ev
         */
        onClickUnlink(ev) {
            if (!this.attachment) {
                return;
            }
            if (this.attachmentList.composerViewOwner) {
                this.attachment.remove();
            } else {
                this.update({ attachmentDeleteConfirmDialog: insertAndReplace() });
            }
        },
        /**
         * @private
         * @returns {number|FieldCommand}
         */
        _computeHeight() {
            if (!this.attachment) {
                return clear();
            }
            if (this.attachment.composer) {
                return 50;
            }
            return 160;
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeImageUrl() {
            if (!this.attachment) {
                return clear();
            }
            if (!this.attachment.accessToken && this.attachment.originThread && this.attachment.originThread.model === 'mail.channel') {
                return `/mail/channel/${this.attachment.originThread.id}/image/${this.attachment.id}/${this.width}x${this.height}?checksum=${this.attachment.checksum}`;
            }
            const accessToken = this.attachment.accessToken ? `?access_token=${this.attachment.accessToken}&checksum=${this.attachment.checksum}` : `?checksum=${this.attachment.checksum}`;
            return `/web/image/${this.attachment.id}/${this.width}x${this.height}${accessToken}`;
        },
        /**
         * @private
         * @returns {number|FieldCommand}
         */
        _computeWidth() {
            if (!this.attachment) {
                return clear();
            }
            return 160;
        },
    },
    fields: {
        /**
         * Determines the attachment of this link preview.
         */
        attachment: one('Attachment', {
            readonly: true,
            required: true,
        }),
        attachmentDeleteConfirmDialog: one('Dialog', {
            inverse: 'attachmentLinkPreviewOwnerAsAttachmentDeleteConfirm',
            isCausal: true,
        }),
        /**
         * Determines the attachmentList for this link preview.
         */
        attachmentList: one('AttachmentList', {
            inverse: 'attachmentLinkPreviewViews',
            readonly: true,
            required: true,
        }),
        /**
         * States the status of the delete confirm dialog (open/closed).
         */
        hasDeleteConfirmDialog: attr({
            default: false,
        }),
        /**
         * Determines the max height of this attachment image in px.
         */
        height: attr({
            compute: '_computeHeight',
            required: true,
        }),
        imageUrl: attr({
            compute: '_computeImageUrl',
        }),
        /**
         * Determines the max width of this attachment image in px.
         */
        width: attr({
            compute: '_computeWidth',
            required: true,
        }),
    }
});
