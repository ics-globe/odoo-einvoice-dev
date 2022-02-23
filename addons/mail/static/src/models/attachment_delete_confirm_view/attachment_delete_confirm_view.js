/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentDeleteConfirmView',
    identifyingFields: [['attachmentCardAttachmentDeleteConfirmDialogOwner', 'attachmentImageAttachmentDeleteConfirmDialogOwner']],
    recordMethods: {
        /**
         * Returns whether the given html element is inside this attachment delete confirm view.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        containsElement(element) {
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
        },
        onClickCancel() {
            if (this.attachmentCardAttachmentDeleteConfirmDialogOwner) {
                this.attachmentCardAttachmentDeleteConfirmDialogOwner.delete();
            }
            if (this.attachmentImageAttachmentDeleteConfirmDialogOwner) {
                this.attachmentImageAttachmentDeleteConfirmDialogOwner.delete();
            }
        },
        async onClickOk() {
            await this.attachment.remove();
            if (this.chatter && this.chatter.component) {
                this.chatter.component.trigger('o-attachments-changed');
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeAttachment() {
            if (this.attachmentCardAttachmentDeleteConfirmDialogOwner) {
                return replace(this.attachmentCardAttachmentDeleteConfirmDialogOwner.attachmentCardOwner.attachment);
            }
            if (this.attachmentImageAttachmentDeleteConfirmDialogOwner) {
                return replace(this.attachmentImageAttachmentDeleteConfirmDialogOwner.attachmentImageOwner.attachment);
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeBody() {
            return _.str.sprintf(this.env._t(`Do you really want to delete "%s"?`), this.attachment.displayName);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeChatter() {
            if (
                this.attachmentCardAttachmentDeleteConfirmDialogOwner &&
                this.attachmentCardAttachmentDeleteConfirmDialogOwner.attachmentCardOwner.attachmentList.attachmentBoxViewOwner &&
                this.attachmentCardAttachmentDeleteConfirmDialogOwner.attachmentCardOwner.attachmentList.attachmentBoxViewOwner.chatter
            ) {
                return replace(this.attachmentCardAttachmentDeleteConfirmDialogOwner.attachmentCardOwner.attachmentList.attachmentBoxViewOwner.chatter);
            }
            if (
                this.attachmentImageAttachmentDeleteConfirmDialogOwner &&
                this.attachmentImageAttachmentDeleteConfirmDialogOwner.attachmentImageOwner.attachmentList.attachmentBoxViewOwner &&
                this.attachmentImageAttachmentDeleteConfirmDialogOwner.attachmentImageOwner.attachmentList.attachmentBoxViewOwner.chatter
            ) {
                return replace(this.attachmentImageAttachmentDeleteConfirmDialogOwner.attachmentImageOwner.attachmentList.attachmentBoxViewOwner.chatter);
            }
            return clear();
        },
    },
    fields: {
        attachment: one('Attachment', {
            compute: '_computeAttachment',
            readonly: true,
            required: true,
        }),
        body: attr({
            compute: '_computeBody',
        }),
        chatter: one('Chatter', {
            compute: '_computeChatter',
        }),
        component: attr(),
        // TODO SEB make model common to both
        attachmentCardAttachmentDeleteConfirmDialogOwner: one('AttachmentCard.AttachmentDeleteConfirmDialog', {
            inverse: 'attachmentDeleteConfirmView',
            readonly: true,
        }),
        attachmentImageAttachmentDeleteConfirmDialogOwner: one('AttachmentImage.AttachmentDeleteConfirmDialog', {
            inverse: 'attachmentDeleteConfirmView',
            readonly: true,
        }),
    },
});
