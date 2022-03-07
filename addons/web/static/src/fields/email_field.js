/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class EmailField extends Component {
    /**
     * @param {Event} ev
     */
    onChange(ev) {
        this.props.update(ev.target.value);
    }
}

EmailField.template = "web.EmailField";
EmailField.props = {
    ...standardFieldProps,
};
EmailField.displayName = _lt("Email");
EmailField.supportedTypes = ["char"];

registry.category("fields").add("email", EmailField);
