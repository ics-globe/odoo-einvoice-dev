/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { isFalsy } from "@web/core/utils/xml";

const { Component } = owl;

export class BooleanFavoriteField extends Component {}

BooleanFavoriteField.template = "web.BooleanFavoriteField";
BooleanFavoriteField.props = {
    noLabel: { type: Boolean, optional: true },
    update: { type: Function, optional: true },
    value: Boolean,
};
BooleanFavoriteField.defaultProps = {
    noLabel: false,
    update: () => {},
};

BooleanFavoriteField.displayName = _lt("Favorite");
BooleanFavoriteField.supportedTypes = ["boolean"];

BooleanFavoriteField.isEmpty = () => false;
BooleanFavoriteField.computeProps = (params) => {
    return {
        noLabel: isFalsy(params.attrs.noLabel),
        update: params.update,
        value: params.value,
    };
};

registry.category("fields").add("boolean_favorite", BooleanFavoriteField);
