/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

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
        _onChangeCheckConstraints() {
            // TODO move to field itself, with identifying flag
            for (const identifyingField of this.identifyingFieldsFlattened) {
                if (identifyingField.model !== this) {
                    throw new Error(`Identifying field "${identifyingField}" is not a field on ${this}.`);
                }
                if (!identifyingField.readonly) {
                    throw new Error(`Identifying field "${identifyingField}" is lacking readonly.`);
                }
                if (identifyingField.type === 'relation' && identifyingField.relationType !== 'one') {
                    throw new Error(`Identifying field "${identifyingField}" has a relation of type "${identifyingField.relationType}" but identifying field is only supported for "one".`);
                }
                for (const inverseField of identifyingField.inverses) {
                    if (!inverseField.isCausal) {
                        throw new Error(`Identifying field "${identifyingField}" has an inverse "${inverseField}" not declared as "isCausal".`);
                    }
                }
            }
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
    onChanges: [
        new OnChange({
            dependencies: ['identifyingFieldsFlattened'],
            methodName: '_onChangeCheckConstraints',
        }),
    ],
});
