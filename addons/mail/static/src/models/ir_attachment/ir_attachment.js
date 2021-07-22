  /** @odoo-module **/

import { registerFieldPatchModel, registerInstancePatchModel } from '@discuss/model/model_core';
import { many2many, many2one } from '@discuss/model/model_field';
import { replace } from '@discuss/model/model_field_command';

registerInstancePatchModel('ir.attachment', 'mail', {
    /**
     * @override
     */
    _created() {
        this._super();
        if (this.isUploading) {
            return;
        }
        const relatedUploadingAttachment = this.env.models['ir.attachment']
            .find(attachment =>
                attachment.filename === this.filename &&
                attachment.isUploading
            );
        if (!relatedUploadingAttachment) {
            return;
        }
        const mailMessageComposers = relatedUploadingAttachment.mailMessageComposers;
        relatedUploadingAttachment.delete();
        this.update({ mailMessageComposers: replace(mailMessageComposers) });
    },
});

registerFieldPatchModel('ir.attachment', 'mail', {
    activities: many2many('mail.activity', {
        inverse: 'attachments',
    }),
    mailMessageComposers: many2many('mail.composer', {
        inverse: 'attachments',
    }),
    mailMessages: many2many('mail.message', {
        inverse: 'attachments',
    }),
    originThread: many2one('mail.thread', {
        inverse: 'originThreadAttachments',
    }),
    threads: many2many('mail.thread', {
        inverse: 'attachments',
    }),
});
