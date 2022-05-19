/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { isTruthy } from "../core/utils/xml";
import { formatChar } from "./formatters";
import { useInputField } from "./input_field_hook";
import { TranslationButton } from "./translation_button";

const { Component } = owl;

export class CharField extends Component {
    setup() {
        useInputField({ getValue: () => this.props.value || "", parse: (v) => this.parse(v) });
    }

    get formattedValue() {
        return formatChar(this.props.value, { isPassword: this.props.isPassword });
    }

    parse(value) {
        if (this.props.shouldTrim) {
            return value.trim();
        }
        return value;
    }
    /**
     * @param {Event} ev
     */
    onChange(ev) {
        let value = this.parse(ev.target.value);
        this.props.update(value || false);
    }
}

CharField.template = "web.CharField";
CharField.props = {
    autocomplete: { type: String, optional: true },
    isPassword: { type: Boolean, optional: true },
    isTranslatable: { type: Boolean, optional: true },
    maxLength: { type: Number, optional: true },
    name: { type: String, optional: true },
    placeholder: { type: String, optional: true },
    readonly: { type: Boolean, optional: true },
    resId: { type: [Number, Boolean], optional: true },
    resModel: { type: String, optional: true },
    shouldTrim: { type: Boolean, optional: true },
    update: { type: Function, optional: true },
    value: [String, false],
};
CharField.components = {
    TranslationButton,
};
CharField.displayName = _lt("Text");
CharField.supportedTypes = ["char"];

CharField.computeProps = (params) => {
    return {
        autocomplete: params.attrs.autocomplete,
        isPassword: isTruthy(params.attrs.password),
        isTranslatable: params.field.translate,
        maxLength: params.field.size,
        name: params.name,
        placeholder: params.attrs.placeholder,
        readonly: params.readonly,
        resId: params.record.resId,
        resModel: params.record.resModel,
        shouldTrim: params.field.trim,
        update: params.update,
        value: params.value,
    };
};

registry.category("fields").add("char", CharField);
