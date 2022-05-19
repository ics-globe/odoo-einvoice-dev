/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useInputField } from "./input_field_hook";
import { useNumpadDecimal } from "./numpad_decimal_hook";
import { formatFloat } from "./formatters";
import { parseFloat } from "./parsers";

const { Component, onWillUpdateProps } = owl;
export class FloatField extends Component {
    setup() {
        this.defaultInputValue = this.getFormattedValue();
        useInputField({
            getValue: () => this.defaultInputValue,
            refName: "numpadDecimal",
            parse: (v) => this.parse(v),
        });
        useNumpadDecimal();
        onWillUpdateProps((nextProps) => {
            if (
                nextProps.readonly !== this.props.readonly &&
                !nextProps.readonly &&
                nextProps.inputType !== "number"
            ) {
                this.defaultInputValue = this.getFormattedValue(nextProps);
            }
        });
    }

    parse(value) {
        return this.props.inputType === "number" ? Number(value) : parseFloat(value);
    }

    onChange(ev) {
        let isValid = true;
        let value = ev.target.value;
        try {
            value = this.parse(value);
        } catch (_e) {
            // WOWL TODO: rethrow error when not the expected type
            isValid = false;
            this.props.invalidate();
        }
        if (isValid) {
            this.props.update(value);
            this.defaultInputValue = ev.target.value;
        }
    }

    getFormattedValue(props = this.props) {
        if (props.inputType === "number" && !props.readonly && props.value) {
            return props.value;
        }
        return formatFloat(props.value, { digits: props.digits });
    }
}

FloatField.template = "web.FloatField";
FloatField.props = {
    digits: { type: Array, optional: true },
    inputType: { type: String, optional: true },
    invalidate: { type: Function, optional: true },
    readonly: { type: Boolean, optional: true },
    step: { type: Number, optional: true },
    update: { type: Function, optional: true },
    value: Number,
};
FloatField.defaultProps = {
    inputType: "text",
    invalidate: () => {},
    readonly: false,
    step: 1,
    update: () => {},
};

FloatField.supportedTypes = ["float"];

FloatField.isEmpty = () => false;
FloatField.computeProps = (params) => {
    return {
        // Sadly, digits param was available as an option and an attr.
        // The option version could be removed with some xml refactoring.
        digits:
            (params.attrs.digits ? JSON.parse(params.attrs.digits) : params.attrs.options.digits) ||
            params.field.digits,
        inputType: params.attrs.options.type,
        invalidate: () => params.record.setInvalidField(params.name),
        readonly: params.readonly,
        step: params.attrs.options.step,
        update: params.update,
        value: params.value,
    };
};

registry.category("fields").add("float", FloatField);
