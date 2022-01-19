/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'ModelRelationArrowView',
    identifyingFields: ['fieldViewOwner'],
    recordMethods: {
        /**
         * @private
         * @returns {number}
         */
        _computeHeight() {
            return Math.abs(this.positionEndVertical - this.positionStartVertical) + this.svgMargin * 2;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsIdentifyingField() {
            return (
                (this.fieldViewOwner && this.fieldViewOwner.isIdentifyingField) ||
                (this.fieldInverseView && this.fieldInverseView.isIdentifyingField)
            );
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeModelGraphView() {
            return replace(this.fieldViewOwner.modelViewOwner.modelGraphViewOwner);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeModelRelationArrowViewAsInverse() {
            if (!this.modelGraphView) {
                return clear();
            }
            const inverseModelView = this.models['ModelView'].findFromIdentifyingData({
                model: this.models[this.fieldViewOwner.field.to],
                modelGraphViewOwner: replace(this.modelGraphView),
            });
            if (!inverseModelView) {
                return clear();
            }
            return replace(this.models['ModelFieldView'].findFromIdentifyingData({
                field: inverseModelView.model.fields[this.fieldViewOwner.field.inverse],
                modelViewOwner: replace(inverseModelView),
            }));
        },
        /**
         * @private
         * @returns {number}
         */
        _computePositionEndHorizontal() {
            if (!this.fieldInverseView) {
                return clear();
            }
            return this.fieldInverseView.positionHorizontal;
        },
        /**
         * @private
         * @returns {number}
         */
        _computePositionEndVertical() {
            if (!this.fieldInverseView) {
                return clear();
            }
            return this.fieldInverseView.positionVertical;
        },
        _computePositionHorizontal() {
            return Math.min(this.positionStartHorizontal, this.positionEndHorizontal) - this.svgMargin;
        },
        /**
         * @private
         * @returns {number}
         */
        _computePositionStartHorizontal() {
            return this.fieldViewOwner.positionHorizontal;
        },
        /**
         * @private
         * @returns {number}
         */
        _computePositionStartVertical() {
            return this.fieldViewOwner.positionVertical;
        },
        /**
         * @private
         * @returns {number}
         */
        _computePositionVertical() {
            return Math.min(this.positionStartVertical, this.positionEndVertical) - this.svgMargin;
        },
        /**
         * @private
         * @returns {number}
         */
        _computeSvgArrowEndHorizontal() {
            return this.positionStartHorizontal < this.positionEndHorizontal ? 0 + this.svgMargin : this.width - this.svgMargin;
        },
        /**
         * @private
         * @returns {number}
         */
        _computeSvgArrowEndVertical() {
            return this.positionStartVertical < this.positionEndVertical ? 0 + this.svgMargin : this.height - this.svgMargin;
        },
        /**
         * @private
         * @returns {number}
         */
        _computeSvgArrowStartHorizontal() {
            return this.positionStartHorizontal > this.positionEndHorizontal ? 0 + this.svgMargin : this.width - this.svgMargin;
        },
        /**
         * @private
         * @returns {number}
         */
        _computeSvgArrowStartVertical() {
            return this.positionStartVertical > this.positionEndVertical ? 0 + this.svgMargin : this.height - this.svgMargin;
        },
        /**
         * @private
         * @returns {number}
         */
        _computeWidth() {
            return Math.abs(this.positionEndHorizontal - this.positionStartHorizontal) + this.svgMargin * 2;
        },
    },
    fields: {
        fieldViewOwner: one2one('ModelFieldView', {
            inverse: 'modelRelationArrowView',
            readonly: true,
            required: true,
        }),
        fieldInverseView: one2one('ModelFieldView', {
            compute: '_computeModelRelationArrowViewAsInverse',
            inverse: 'modelRelationArrowViewAsInverse',
            readonly: true,
            required: true,
        }),
        height: attr({
            compute: '_computeHeight',
        }),
        isIdentifyingField: attr({
            compute: '_computeIsIdentifyingField',
        }),
        modelGraphView: many2one('ModelGraphView', {
            compute: '_computeModelGraphView',
            inverse: 'modelRelationArrowViews',
            readonly: true,
            required: true,
        }),
        positionEndVertical: attr({
            compute: '_computePositionEndVertical',
        }),
        positionEndHorizontal: attr({
            compute: '_computePositionEndHorizontal',
        }),
        positionHorizontal: attr({
            compute: '_computePositionHorizontal',
        }),
        positionStartHorizontal: attr({
            compute: '_computePositionStartHorizontal',
        }),
        positionStartVertical: attr({
            compute: '_computePositionStartVertical',
        }),
        positionVertical: attr({
            compute: '_computePositionVertical',
        }),
        svgArrowEndHorizontal: attr({
            compute: '_computeSvgArrowEndHorizontal',
        }),
        svgArrowEndVertical: attr({
            compute: '_computeSvgArrowEndVertical',
        }),
        svgArrowStartHorizontal: attr({
            compute: '_computeSvgArrowStartHorizontal',
        }),
        svgArrowStartVertical: attr({
            compute: '_computeSvgArrowStartVertical',
        }),
        svgMargin: attr({
            default: 10,
        }),
        width: attr({
            compute: '_computeWidth',
        }),
    },
});
