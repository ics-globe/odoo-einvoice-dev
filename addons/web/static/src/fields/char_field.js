/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class CharField extends Component {
    get formattedValue() {
        let value = typeof this.props.value === "string" ? this.props.value : "";
        if (this.props.isPassword) {
            value = "*".repeat(value.length);
        }
        return value;
    }
    get shouldTrim() {
        return this.props.record.fields[this.props.name].trim;
    }
    get maxLength() {
        return this.props.record.fields[this.props.name].size;
    }

    /**
     * @param {Event} ev
     */
    onChange(ev) {
        let value = ev.target.value;
        if (this.shouldTrim) {
            value = value.trim();
        }
        this.props.update(value || false);
    }
}

Object.assign(CharField, {
    template: "web.CharField",
    props: {
        ...standardFieldProps,
        autocomplete: { type: String, optional: true },
        isPassword: { type: Boolean, optional: true },
        placeholder: { type: String, optional: true },
    },

    displayName: _lt("Text"),
    supportedTypes: ["char"],

    convertAttrsToProps(attrs) {
        return {
            autocomplete: attrs.autocomplete,
            isPassword: "password" in attrs,
            placeholder: attrs.placeholder,
        };
    },
});

CharField.template = "web.CharField";

registry.category("fields").add("char", CharField);
