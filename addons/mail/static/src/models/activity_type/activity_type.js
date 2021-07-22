/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr, one2many } from '@discuss/model/model_field';

function factory(dependencies) {

    class ActivityType extends dependencies['discuss.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

    }

    ActivityType.fields = {
        activities: one2many('mail.activity', {
            inverse: 'type',
        }),
        displayName: attr(),
        id: attr({
            required: true,
        }),
    };

    ActivityType.modelName = 'mail.activity_type';

    return ActivityType;
}

registerNewModel('mail.activity_type', factory);
