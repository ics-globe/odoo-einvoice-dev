/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { one2many } from '@discuss/model/model_field';
import { link } from '@discuss/model/model_field_command';

function factory(dependencies) {

    class DiscussDialogManager extends dependencies['discuss.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {string} modelName
         * @param {Object} [recordData]
         */
        open(modelName, recordData) {
            if (!modelName) {
                throw new Error("Dialog should have a link to a model");
            }
            const Model = this.env.models[modelName];
            if (!Model) {
                throw new Error(`No model exists with name ${modelName}`);
            }
            const record = Model.create(recordData);
            const dialog = this.env.models['discuss.dialog'].create({
                manager: link(this),
                record: link(record),
            });
            return dialog;
        }

    }

    DiscussDialogManager.fields = {
        // FIXME: dependent on implementation that uses insert order in relations!!
        dialogs: one2many('discuss.dialog', {
            inverse: 'manager',
            isCausal: true,
        }),
    };

    DiscussDialogManager.modelName = 'discuss.dialog_manager';

    return DiscussDialogManager;
}

registerNewModel('discuss.dialog_manager', factory);
