/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class AttachmentLinkPreview extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {AttachmentLinkPreviewView}
     */
    get attachmentLinkPreviewView() {
        return this.props.record;
    }

}

Object.assign(AttachmentLinkPreview, {
    props: { record: Object },
    template: 'mail.AttachmentLinkPreview',
});

registerMessagingComponent(AttachmentLinkPreview);
