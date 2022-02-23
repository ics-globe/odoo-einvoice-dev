/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'AttachmentImage.AttachmentDeleteConfirmDialog',
    identifyingFields: ['attachmentImageOwner'],
    recordMethods: {
        _computeDialog() {
            return insertAndReplace({
                componentClassName: 'o_Dialog_componentMediumSize align-self-start mt-5', // TODO SEB should be saved on record?
                componentName: 'AttachmentDeleteConfirm', // TODO SEB should BE record (component = model)
                record: replace(this.attachmentDeleteConfirmView),
            });
        },
    },
    fields: {
        attachmentImageOwner: one('AttachmentImage', {
            inverse: 'attachmentDeleteConfirmDialog',
            readonly: true,
            required: true,
        }),
        attachmentDeleteConfirmView: one('AttachmentDeleteConfirmView', {
            default: insertAndReplace(),
            inverse: 'attachmentImageAttachmentDeleteConfirmDialogOwner',
            isCausal: true,
            readonly: true,
            required: true,
        }),
        dialog: one('Dialog', {
            compute: '_computeDialog',
            inverse: 'owner',
            isCausal: true,
            readonly: true,
            required: true,
        }),
    },
});
