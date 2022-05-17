/** @odoo-module **/

import { useHotkey } from "../hotkeys/hotkey_hook";

const { Component } = owl;

/**
 * Custom checkbox
 *
 * <CheckBox
 *    value="boolean"
 *    disabled="boolean"
 *    onChange="_onValueChange"
 *    >
 *    Change the label text
 *  </CheckBox>
 *
 * @extends Component
 */

export class CheckBox extends Component {
    setup() {
        this.id = `checkbox-comp-${CheckBox.nextId++}`;
        useHotkey(
            "Enter",
            ({ reference }) => {
                const oldValue = reference.querySelector("input").checked;
                this.props.onChange(!oldValue);
            },
            { reference: "root", bypassEditableProtection: true }
        );
    }

    onChange(ev) {
        if (this.props.disabled) {
            // When a click is triggered on an input directly with
            // Javascript, the disabled attribute is not respected
            // and the value is changed. This assures a disabled
            // CheckBox can't be forced to update
            ev.target.checked = !ev.target.checked;
            return;
        }
        this.props.onChange(ev.target.checked);
    }
}

CheckBox.template = "web.CheckBox";
CheckBox.nextId = 1;
CheckBox.defaultProps = {
    onChange: () => {},
};
CheckBox.props = {
    id: {
        type: true,
        optional: true,
    },
    disabled: {
        type: Boolean,
        optional: true,
    },
    value: {
        type: Boolean,
        optional: true,
    },
    slots: {
        type: Object,
        optional: true,
    },
    onChange: {
        type: Function,
        optional: true,
    },
    className: {
        type: String,
        optional: true,
    },
};
