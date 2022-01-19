/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one2many, one2one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ModelGraphView',
    identifyingFields: ['discussOwner'],
    recordMethods: {
        onComponentUpdate() {
            this.updatePositions();
        },
        onInput(ev) {
            this.update({ filterString: ev.target.value });
        },
        updatePositions() {
            for (const modelView of this.modelViews) {
                modelView.updatePositions();
            }
        },
        /**
         * @private
         * @returns {Array[ModelClass]}
         */
        _computeAllModels() {
            return Object.values(this.models);
        },
        /**
         * @private
         * @returns {Array[ModelClass]}
         */
        _computeFilteredModels() {
            return [...new Set(this.allModels.filter(model => {
                if (!this.filterString) {
                    return true;
                }
                for (const part of this.filterString.split(',')) {
                    if (model.name.toLowerCase() === part.trim().toLowerCase()) {
                        return true;
                    }
                }
                return false;
            }).concat(this.modelsFromSelectedRelations))];
        },
        /**
         * @private
         * @returns {Array[ModelClass]}
         */
        _computeModelsFromSelectedRelations() {
            const modelsSet = new Set();
            for (const modelView of this.modelViews) {
                for (const modelFieldView of modelView.modelFieldViews) {
                    if (modelFieldView.isSelected) {
                        modelsSet.add(modelView.model);
                        modelsSet.add(this.models[modelFieldView.field.to]);
                    }
                }
            }
            return [...modelsSet];
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeModelViews() {
            return insertAndReplace(this.filteredModels.map(model => {
                return {
                    model,
                };
            }));
        },
    },
    fields: {
        allModels: attr({
            compute: '_computeAllModels',
        }),
        discussOwner: one2one('Discuss', {
            inverse: 'modelGraphView',
            readonly: true,
            required: true,
        }),
        filteredModels: attr({
            compute: '_computeFilteredModels',
        }),
        filterString: attr({
            default: '',
        }),
        modelRelationArrowViews: one2many('ModelRelationArrowView', {
            inverse: 'modelGraphView',
            isCausal: true,
            readonly: true,
        }),
        modelsFromSelectedRelations: attr({
            compute: '_computeModelsFromSelectedRelations',
            default: [],
        }),
        modelViews: one2many('ModelView', {
            compute: '_computeModelViews',
            inverse: 'modelGraphViewOwner',
            isCausal: true,
        }),
    },
});
