/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'ModelFieldView',
    identifyingFields: ['modelViewOwner', 'field'],
    recordMethods: {
        onClickSelect() {
            this.update({ isSelected: true });
        },
        onClickUnselect() {
            this.update({ isSelected: false });
        },
        onComponentUpdate() {
            this.update({ hasComponentEl: true });
            this.updatePosition();
        },
        updatePosition() {
            this.update({
                positionHorizontal: this.nameRef && this.nameRef.el ? Math.round(this.nameRef.el.offsetLeft + this.nameRef.el.offsetWidth) : clear(),
                positionVertical: this.nameRef && this.nameRef.el ? Math.round(this.nameRef.el.offsetTop + this.nameRef.el.offsetHeight / 2) : clear(),
            });
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsIdentifyingField() {
            return this.modelViewOwner.model.__identifyingFieldsFlattened.has(this.field.fieldName);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsInverseIdentifyingField() {
            if (!this.field.to) {
                return clear();
            }
            return this.models[this.field.to].__identifyingFieldsFlattened.has(this.field.inverse);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeModelRelationArrowView() {
            if (!this.isSelected || !this.field.to || !this.hasComponentEl) {
                return clear();
            }
            const inverseModelView = this.models['ModelView'].findFromIdentifyingData({
                model: this.models[this.field.to],
                modelGraphViewOwner: replace(this.modelViewOwner.modelGraphViewOwner),
            });
            if (!inverseModelView) {
                return clear();
            }
            const inverseFieldView = this.models['ModelFieldView'].findFromIdentifyingData({
                field: inverseModelView.model.fields[this.field.inverse],
                modelViewOwner: replace(inverseModelView),
            });
            if (!inverseFieldView || !inverseFieldView.hasComponentEl) {
                return clear();
            }
            return insertAndReplace();
        },
    },
    fields: {
        component: attr(),
        field: attr({
            readonly: true,
            required: true,
        }),
        hasComponentEl: attr(),
        isIdentifyingField: attr({
            compute: '_computeIsIdentifyingField',
        }),
        isInverseIdentifyingField: attr({
            compute: '_computeIsInverseIdentifyingField',
        }),
        isSelected: attr({
            default: false,
        }),
        modelViewOwner: many2one('ModelView', {
            inverse: 'modelFieldViews',
            readonly: true,
            required: true,
        }),
        modelRelationArrowView: one2one('ModelRelationArrowView', {
            compute: '_computeModelRelationArrowView',
            inverse: 'fieldViewOwner',
            isCausal: true,
            readonly: true,
        }),
        modelRelationArrowViewAsInverse: one2one('ModelRelationArrowView', {
            inverse: 'fieldInverseView',
            isCausal: true,
            readonly: true,
        }),
        nameRef: attr(),
        positionHorizontal: attr(),
        positionVertical: attr(),
    },
});
