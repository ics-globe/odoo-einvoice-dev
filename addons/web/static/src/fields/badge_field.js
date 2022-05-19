/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const { Component } = owl;
const formatters = registry.category("formatters");

export class BadgeField extends Component {
    get classFromDecoration() {
        for (const decorationName in this.props.decorations) {
            if (this.props.decorations[decorationName]) {
                return `bg-${decorationName}-light`;
            }
        }
        return "";
    }
}

BadgeField.template = "web.BadgeField";
BadgeField.props = {
    decorations: {
        optional: true,
        type: Object,
        shape: {
            danger: { type: Boolean, optional: true },
            info: { type: Boolean, optional: true },
            muted: { type: Boolean, optional: true },
            success: { type: Boolean, optional: true },
            warning: { type: Boolean, optional: true },
            "*": true,
        },
    },
    text: String,
};
BadgeField.defaultProps = {
    decorations: {},
};

BadgeField.displayName = _lt("Badge");
BadgeField.supportedTypes = ["selection", "many2one", "char"];

BadgeField.computeProps = (params) => {
    const formatter = formatters.get(params.field.type);
    return {
        decorations: params.decorations,
        text: formatter(params.value, { selection: params.field.selection }),
    };
};

registry.category("fields").add("badge", BadgeField);
