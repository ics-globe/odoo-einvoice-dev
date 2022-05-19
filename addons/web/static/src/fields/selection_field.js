/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { formatSelection } from "./formatters";

const { Component } = owl;

export class SelectionField extends Component {
    get string() {
        return formatSelection(this.props.value, { selection: this.props.options });
    }

    serializeOption(value) {
        return JSON.stringify(value);
    }
    deserializeOption(value) {
        return JSON.parse(value);
    }

    /**
     * @param {Event} ev
     */
    onChange(ev) {
        const newValue = this.deserializeOption(ev.target.value);
        return this.props.update(newValue);
    }
}

SelectionField.template = "web.SelectionField";
SelectionField.props = {
    options: {
        type: Array,
        element: Array,
    },
    readonly: { type: Boolean, optional: true },
    update: { type: Function, optional: true },
    value: [String, Number, false],
};
SelectionField.defaultProps = {
    readonly: false,
    update: () => {},
};

SelectionField.displayName = _lt("Selection");
SelectionField.supportedTypes = ["many2one", "selection"];

SelectionField.isEmpty = (record, fieldName) => record.data[fieldName] === false;
SelectionField.computeProps = (params) => {
    let options = null;
    let value = null;
    let update = null;

    switch (params.field.type) {
        case "many2one": {
            options = Array.from(params.record.preloadedData[params.name]);
            value = params.value && params.value[0];
            update = (newValue) =>
                params.update(newValue && options.find((o) => o[0] === newValue));
            break;
        }
        case "selection": {
            options = Array.from(params.field.selection);
            value = params.value;
            update = params.update;
            break;
        }
        default: {
            throw new Error(`Unsupported type "${params.field.type}" for SelectionField`);
        }
    }

    if (!params.required) {
        options.unshift([false, params.attrs.placeholder || ""]);
    }

    return {
        options,
        readonly: params.readonly,
        update,
        value,
    };
};

registry.category("fields").add("selection", SelectionField);

export function preloadSelection(orm, record, fieldName) {
    const field = record.fields[fieldName];
    const context = record.evalContext;
    const domain = record.getFieldDomain(fieldName).toList(context);
    return orm.call(field.relation, "name_search", ["", domain]);
}

registry.category("preloadedData").add("selection", {
    loadOnTypes: ["many2one"],
    preload: preloadSelection,
});
