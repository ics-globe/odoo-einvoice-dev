/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr } from '@discuss/model/model_field';

function factory(dependencies) {

    class Locale extends dependencies['discuss.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeLanguage() {
            return this.env._t.database.parameters.code;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeTextDirection() {
            return this.env._t.database.parameters.direction;
        }

    }

    Locale.fields = {
        /**
         * Language used by interface, formatted like {language ISO 2}_{country ISO 2} (eg: fr_FR).
         */
        language: attr({
            compute: '_computeLanguage',
        }),
        textDirection: attr({
            compute: '_computeTextDirection',
        }),
    };

    Locale.modelName = 'discuss.locale';

    return Locale;
}

registerNewModel('discuss.locale', factory);
