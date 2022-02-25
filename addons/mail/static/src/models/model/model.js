/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';

registerModel({
    name: 'Model',
    identifyingFields: ['name'],
    recordMethods: {
        _computeIdentifyingFieldsFlattened() {
            const identifyingFieldsFlattened = new Set();
            for (const identifyingElement of this.identifyingFields) {
                const identifyingFields = typeof identifyingElement === 'string'
                    ? [identifyingElement]
                    : identifyingElement;
                for (const identifyingField of identifyingFields) {
                    const field = this.models['Model.Field'].findFromIdentifyingData({
                        model: replace(this),
                        name: identifyingField,
                    });
                    identifyingFieldsFlattened.add(field);
                }
            }
            return replace(identifyingFieldsFlattened);
        },
    },
    fields: {
        identifyingFields: attr({
            required: true,
        }),
        identifyingFieldsFlattened: many('Model.Field', {
            compute: '_computeIdentifyingFieldsFlattened',
            inverse: 'modelAsIdentifyingField',
        }),
        modelFields: many('Model.Field', {
            inverse: 'model',
            isCausal: true,
        }),
        name: attr({
            readonly: true,
            required: true,
        }),
        records: many('Record', {
            inverse: 'model2',
            isCausal: true,
        }),
    },
});
