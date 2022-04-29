/** @odoo-module */
import { useViewButtons } from "@web/views/view_button/hook";
import { createElement } from "@web/core/utils/xml";
import { FormRenderer } from "@web/views/form/form_renderer";
import { ViewButton } from "@web/views/view_button/view_button";
import { Dialog } from "@web/core/dialog/dialog";
import { useBus, useChildRef } from "@web/core/utils/hooks";

const { Component } = owl;

export class X2ManyFieldDialog extends Component {
    setup() {
        super.setup();
        this.archInfo = this.props.archInfo;
        this.record = this.props.record;
        this.title = this.props.title;

        useBus(this.record.model, "update", () => this.render(true));

        this.modalRef = useChildRef();

        const reload = () => this.record.load();
        useViewButtons(this.props.record.model, this.modalRef, { reload }); // maybe pass the model directly in props

        if (this.archInfo.xmlDoc.querySelector("footer")) {
            this.footerArchInfo = Object.assign({}, this.archInfo);
            this.footerArchInfo.xmlDoc = createElement("t");
            this.footerArchInfo.xmlDoc.append(
                ...[...this.archInfo.xmlDoc.querySelectorAll("footer")]
            );
            this.footerArchInfo.arch = this.footerArchInfo.xmlDoc.outerHTML;
            [...this.archInfo.xmlDoc.querySelectorAll("footer")].forEach((x) => x.remove());
            this.archInfo.arch = this.archInfo.xmlDoc.outerHTML;
        }
    }

    disableButtons() {
        const btns = this.modalRef.el.querySelectorAll(".modal-footer button");
        for (const btn of btns) {
            btn.setAttribute("disabled", "1");
        }
        return btns;
    }

    discard() {
        if (this.record.isInEdition) {
            this.record.discard();
        }
        this.props.close();
    }

    enableButtons(btns) {
        for (const btn of btns) {
            btn.removeAttribute("disabled");
        }
    }

    async save({ saveAndNew }) {
        if (this.record.checkValidity()) {
            this.record = await this.props.save(this.record, { saveAndNew });
        } else {
            return false;
        }
        if (!saveAndNew) {
            this.props.close();
        }
        return true;
    }

    async remove() {
        await this.props.delete();
        this.props.close();
    }

    async saveAndNew() {
        const disabledButtons = this.disableButtons();
        const saved = await this.save({ saveAndNew: true });
        if (saved) {
            this.enableButtons(disabledButtons);
            if (this.title) {
                this.title = this.title.replace(this.env._t("Open:"), this.env._t("New:"));
            }
            this.render(true);
        }
    }
}
X2ManyFieldDialog.components = { Dialog, FormRenderer, ViewButton };
X2ManyFieldDialog.props = {
    archInfo: Object,
    close: Function,
    record: Object,
    save: Function,
    title: String,
    delete: { optional: true },
};
X2ManyFieldDialog.template = "web.X2ManyFieldDialog";
