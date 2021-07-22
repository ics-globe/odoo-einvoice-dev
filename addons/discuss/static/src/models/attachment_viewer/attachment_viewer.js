/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr, many2many, many2one } from '@discuss/model/model_field';

function factory(dependencies) {

    class DiscussAttachmentViewer extends dependencies['discuss.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Close the attachment viewer by closing its linked dialog.
         */
        close() {
            const dialog = this.env.models['discuss.dialog'].find(dialog => dialog.record === this);
            if (dialog) {
                dialog.delete();
            }
        }
    }

    DiscussAttachmentViewer.fields = {
        /**
         * Angle of the image. Changes when the user rotates it.
         */
        angle: attr({
            default: 0,
        }),
        attachment: many2one('ir.attachment'),
        attachments: many2many('ir.attachment', {
            inverse: 'attachmentViewer',
        }),
        /**
         * Determine whether the image is loading or not. Useful to diplay
         * a spinner when loading image initially.
         */
        isImageLoading: attr({
            default: false,
        }),
        /**
         * Scale size of the image. Changes when user zooms in/out.
         */
        scale: attr({
            default: 1,
        }),
    };

    DiscussAttachmentViewer.modelName = 'discuss.attachment_viewer';

    return DiscussAttachmentViewer;
}

registerNewModel('discuss.attachment_viewer', factory);
