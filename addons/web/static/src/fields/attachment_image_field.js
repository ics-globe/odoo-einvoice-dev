/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "../core/l10n/translation";

const { Component } = owl;

export class AttachmentImageField extends Component {}

AttachmentImageField.template = "web.AttachmentImageField";
AttachmentImageField.props = {
    resId: { type: Number, optional: true },
    title: { type: String, optional: true },
};

AttachmentImageField.displayName = _lt("Attachment Image");
AttachmentImageField.supportedTypes = ["many2one"];

AttachmentImageField.computeProps = (params) => {
    return {
        resId: params.value ? params.value[0] : undefined,
        title: params.value ? params.value[1] : undefined,
    };
};

registry.category("fields").add("attachment_image", AttachmentImageField);
