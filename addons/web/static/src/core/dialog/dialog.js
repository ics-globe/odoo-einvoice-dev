/** @odoo-module **/

import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useActiveElement } from "../ui/ui_service";

const { Component, useRef, useChildSubEnv, xml } = owl;

export class Dialog extends Component {
    setup() {
        if (this.constructor === Dialog) {
            throw new Error(
                "Dialog should not be used by itself. Please use the dialog service with a Dialog subclass."
            );
        }
        this.modalRef = useRef("modal");
        useActiveElement("modal");
        useHotkey("escape", () => {
            this.close();
        });
        useChildSubEnv({ inDialog: true });
        this.close = this.close.bind(this);
        this.contentClass = this.constructor.contentClass;
        this.fullscreen = this.constructor.fullscreen;
        this.renderFooter = this.constructor.renderFooter;
        this.renderHeader = this.constructor.renderHeader;
        this.size = this.constructor.size;
        this.technical = this.constructor.technical;
        this.title = this.constructor.title;

        //WOWL: To discuss
        if (this.props.parent) {
            const parent = owl.toRaw(this.props.parent);
            parent.__owl__.willDestroy.push(() => {
                this.close();
            });
        }
    }

    /**
     * Send an event signaling that the dialog should be closed.
     * @private
     */
    close() {
        this.props.close();
    }
}

Dialog.template = "web.Dialog";
Dialog.contentClass = null;
Dialog.fullscreen = false;
Dialog.renderFooter = true;
Dialog.renderHeader = true;
Dialog.size = "modal-lg";
Dialog.technical = true;
Dialog.title = "Odoo";
Dialog.bodyTemplate = xml`<div/>`;
Dialog.footerTemplate = "web.DialogFooterDefault";
Dialog.props = {
    parent: { type: Object, optional: true },
    close: Function,
    isActive: { optional: true },
    "*": true,
};

export class SimpleDialog extends Component {
    setup() {
        useActiveElement("modal");
        useHotkey("escape", () => {
            this.props.close();
        });
        useChildSubEnv({ inDialog: true });
    }
}
SimpleDialog.template = "web.SimpleDialog";
SimpleDialog.props = {
    close: Function,
    isActive: { optional: true },
    "*": true,
};
