/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FloatField } from "./float_field";

export class FloatFactorField extends FloatField {}

FloatFactorField.computeProps = (params) => {
    const props = FloatField.computeProps(params);
    const factor = params.attrs.options.factor;
    return {
        ...props,
        value: props.value * factor,
        update: (newValue) => props.update(newValue / factor),
    };
};

registry.category("fields").add("float_factor", FloatFactorField);
