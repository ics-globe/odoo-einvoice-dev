/** @odoo-module **/

import { fieldValue, firstDefinedFieldValue, replaceOrClear } from '@mail/model/model_compute_method';
import { registerNewModel } from '@mail/model/model_core';
import { many2many, many2one, one2many, one2one } from '@mail/model/model_field';
import { insertAndReplace, replace } from '@mail/model/model_field_command';

function factory(dependencies) {

    class AttachmentList extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        _computeAttachmentImages() {
            return insertAndReplace(this.imageAttachments.map(attachment => {
                return {
                    attachment: replace(attachment),
                };
            }));
        }

        _computeAttachmentCards() {
            return insertAndReplace(this.nonImageAttachments.map(attachment => {
                return {
                    attachment: replace(attachment),
                };
            }));
        }

        /**
         * @returns {mail.attachment[]}
         */
        _computeImageAttachments() {
            return replace(this.attachments.filter(attachment => attachment.isImage));
        }

        /**
         * @returns {mail.attachment[]}
         */
        _computeNonImageAttachments() {
            return replace(this.attachments.filter(attachment => !attachment.isImage));
        }

        /**
         * @returns {mail.attachment[]}
         */
        _computeViewableAttachments() {
            return replace(this.attachments.filter(attachment => attachment.isViewable));
        }

    }

    AttachmentList.fields = {
        /**
         * States the attachments to be displayed by this attachment list.
         */
        attachments: many2many('mail.attachment', {
            compute: replaceOrClear(firstDefinedFieldValue(
                'message.attachments',
                'chatter.thread.allAttachments',
                'composerView.composer.attachments',
            )),
            inverse: 'attachmentLists',
        }),
        /**
         * States the attachment cards that are displaying this nonImageAttachments.
         */
        attachmentCards: one2many('mail.attachment_card', {
            compute: '_computeAttachmentCards',
            inverse: 'attachmentList',
            isCausal: true,
        }),
        /**
         * States the attachment images that are displaying this imageAttachments.
         */
        attachmentImages: one2many('mail.attachment_image', {
            compute: '_computeAttachmentImages',
            inverse: 'attachmentList',
            isCausal: true,
        }),
        /**
         * Determines the attachment viewers displaying this attachment list (if any).
         */
        attachmentViewer: one2many('mail.attachment_viewer', {
            inverse: 'attachmentList',
            isCausal: true,
        }),
        /**
         * Link with a chatter to handle attachments.
         */
        chatter: one2one('mail.chatter', {
            inverse: 'attachmentList',
            readonly: true,
        }),
        /**
         * Link with a composer view to handle attachments.
         */
        composerView: one2one('mail.composer_view', {
            inverse: 'attachmentList',
            readonly: true,
        }),
        /**
         * States the attachment that are an image.
         */
        imageAttachments: many2many('mail.attachment', {
            compute: '_computeImageAttachments',
        }),
        message: many2one('mail.message', {
            compute: replaceOrClear(fieldValue('messageView.message')),
        }),
        /**
         * Link with a message view to handle attachments.
         */
        messageView: one2one('mail.message_view', {
            inverse: 'attachmentList',
            readonly: true,
        }),
        /**
         * States the attachment that are not an image.
         */
        nonImageAttachments: many2many('mail.attachment', {
            compute: '_computeNonImageAttachments',
        }),
        /**
         * States the attachments that can be viewed inside the browser.
         */
        viewableAttachments: many2many('mail.attachment', {
            compute: '_computeViewableAttachments',
        }),
    };
    AttachmentList.identifyingFields = [['composerView', 'messageView', 'chatter']];
    AttachmentList.modelName = 'mail.attachment_list';

    return AttachmentList;
}

registerNewModel('mail.attachment_list', factory);
