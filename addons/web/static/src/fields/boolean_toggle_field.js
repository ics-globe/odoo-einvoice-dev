/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { CheckBox } from "@web/core/checkbox/checkbox";

const { Component } = owl;

export class BooleanToggleField extends Component {
    /**
     * @param {{ key: string }} params
     */
    onKeydown({ key }) {
        switch (key) {
            case "Enter":
                this.props.update(!this.props.value);
                break;
        }
    }
}

BooleanToggleField.template = "web.BooleanToggleField";
BooleanToggleField.components = { CheckBox };
BooleanToggleField.props = {
    readonly: { type: Boolean, optional: true },
    update: { type: Function, optional: true },
    value: Boolean,
};
BooleanToggleField.defaultProps = {
    readonly: false,
    update: () => {},
};
BooleanToggleField.displayName = _lt("Toggle");
BooleanToggleField.supportedTypes = ["boolean"];

BooleanToggleField.isEmpty = () => false;
BooleanToggleField.computeProps = (params) => {
    return {
        readonly: params.record.isReadonly(params.name),
        update: params.update,
        value: params.value,
    };
};

registry.category("fields").add("boolean_toggle", BooleanToggleField);
