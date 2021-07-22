/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { many2one, one2one } from '@discuss/model/model_field';

function factory(dependencies) {

    class DiscussDialog extends dependencies['discuss.model'] {}

    DiscussDialog.fields = {
        manager: many2one('discuss.dialog_manager', {
            inverse: 'dialogs',
        }),
        /**
         * Content of dialog that is directly linked to a record that models
         * a UI component, such as AttachmentViewer. These records must be
         * created from @see `discuss.dialog_manager:open()`.
         */
        record: one2one('discuss.model', {
            isCausal: true,
        }),
    };

    DiscussDialog.modelName = 'discuss.dialog';

    return DiscussDialog;
}

registerNewModel('discuss.dialog', factory);
