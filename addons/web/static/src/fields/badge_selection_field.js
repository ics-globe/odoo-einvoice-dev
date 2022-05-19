/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { formatSelection } from "./formatters";

const { Component } = owl;

export class BadgeSelectionField extends Component {
    get string() {
        return formatSelection(this.props.value, { selection: this.props.options });
    }
}

BadgeSelectionField.template = "web.BadgeSelectionField";
BadgeSelectionField.props = {
    options: {
        type: Array,
        element: { type: Array },
    },
    readonly: { type: Boolean, optional: true },
    update: { type: Function, optional: true },
    value: [String, Number, false],
};
BadgeSelectionField.defaultProps = {
    update: () => {},
    readonly: false,
};

BadgeSelectionField.displayName = _lt("Badges");
BadgeSelectionField.supportedTypes = ["many2one", "selection"];

BadgeSelectionField.isEmpty = (record, fieldName) => record.data[fieldName] === false;
BadgeSelectionField.computeProps = (params) => {
    let options = null;
    let update = null;
    let value = null;

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
            throw new Error(`Unsupported type "${params.field.type}" for BadgeSelectionField`);
        }
    }

    return {
        options,
        readonly: params.readonly,
        update,
        value,
    };
};

registry.category("fields").add("selection_badge", BadgeSelectionField);

export function preloadSelection(orm, record, fieldName) {
    const field = record.fields[fieldName];
    const context = record.evalContext;
    const domain = record.getFieldDomain(fieldName).toList(context);
    return orm.call(field.relation, "name_search", ["", domain]);
}

registry.category("preloadedData").add("selection_badge", {
    loadOnTypes: ["many2one"],
    preload: preloadSelection,
});
