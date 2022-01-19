/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many2one, one2many } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ModelView',
    identifyingFields: ['modelGraphViewOwner', 'model'],
    recordMethods: {
        onClickPin() {
            const parts = new Set(this.modelGraphViewOwner.filterString.split(','));
            parts.delete('');
            parts.add(this.model.name);
            this.modelGraphViewOwner.update({ filterString: [...parts].join(',') });
        },
        onClickSelectAll() {
            for (const modelFieldView of this.modelFieldViews) {
                if (modelFieldView.exists()) {
                    modelFieldView.update({ isSelected: true });
                }
            }
        },
        onClickUnpin() {
            const parts = new Set(this.modelGraphViewOwner.filterString.split(','));
            parts.delete(this.model.name);
            this.modelGraphViewOwner.update({ filterString: [...parts].join(',') });
        },
        onClickUnselectAll() {
            for (const modelFieldView of this.modelFieldViews) {
                if (modelFieldView.exists()) {
                    modelFieldView.update({ isSelected: false });
                }
            }
        },
        onComponentUpdate() {
            this.updatePositions();
        },
        updatePositions() {
            for (const modelFieldView of this.modelFieldViews) {
                modelFieldView.updatePosition();
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeModelFieldViews() {
            return insertAndReplace(Object.values(this.model.fields).filter(field => field.to).map(field => {
                return {
                    field,
                };
            }));
        },
    },
    fields: {
        component: attr(),
        model: attr({
            readonly: true,
            required: true,
        }),
        modelFieldViews: one2many('ModelFieldView', {
            compute: '_computeModelFieldViews',
            inverse: 'modelViewOwner',
            isCausal: true,
        }),
        modelGraphViewOwner: many2one('ModelGraphView', {
            inverse: 'modelViews',
            readonly: true,
            required: true,
        }),
    },
});
