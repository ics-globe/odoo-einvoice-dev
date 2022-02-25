/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { OnChange } from '@mail/model/model_onchange';

registerModel({
    name: 'Model.Field',
    identifyingFields: ['model', 'name'],
    fields: {
        compute: attr(),
        default: attr(),
        // many because of generic Record fields...
        inverses: many('Model.Field', {
            inverse: 'inverses',
        }),
        isCausal: attr({
            default: false,
        }),
        model: one('Model', {
            inverse: 'modelFields',
            readonly: true,
            required: true,
        }),
        modelAsIdentifyingField: one('Model', {
            inverse: 'identifyingFieldsFlattened',
        }),
        name: attr({
            readonly: true,
            required: true,
        }),
        readonly: attr({
            default: false,
        }),
        related: attr(),
        relationType: attr(),
        required: attr({
            default: false,
        }),
        sort: attr({

        }),
        type: attr({
            required: true,
        }),
    },
});
