/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr } from '@discuss/model/model_field';
import { clear } from '@discuss/model/model_field_command';

function factory(dependencies) {

    class ResCountry extends dependencies['discuss.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeFlagUrl() {
            if (!this.code) {
                return clear();
            }
            return `/base/static/img/country_flags/${this.code}.png`;
        }

    }

    ResCountry.fields = {
        code: attr(),
        flagUrl: attr({
            compute: '_computeFlagUrl',
            dependencies: [
                'code',
            ],
        }),
        id: attr({
            required: true,
        }),
        name: attr(),
    };

    ResCountry.modelName = 'res.country';

    return ResCountry;
}

registerNewModel('res.country', factory);
