/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { OnChange } from '@mail/model/model_onchange';

registerModel({
    name: 'Model.Field',
    identifyingFields: ['model', 'name'],
    recordMethods: {
        _onChangeCheckConstraints() {
            if (!(['attribute', 'relation'].includes(this.type))) {
                throw new Error(`${this} has unsupported type ${this.type}.`);
            }
            if (this.compute && this.related) {
                throw new Error(`${this} cannot be a related and compute field at the same time.`);
            }
            if (this.type === 'relation') {
                if (!this.relationType) {
                    throw new Error(`${this} must define a relation type in "relationType".`);
                }
                if (!(['many', 'one'].includes(this.relationType))) {
                    throw new Error(`${this} has invalid relation type "${this.relationType}".`);
                }
                if (this.inverses.length === 0) {
                    throw new Error(`${this} must define an inverse relation in "inverse".`);
                }
            }
        },
    },
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
    onChanges: [
        new OnChange({
            dependencies: ['compute', 'related', 'relationType', 'type'],
            methodName: '_onChangeCheckConstraints',
        }),
    ],
});
