/** @odoo-module */

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageTrackingValue extends Component {

    /**
     * @returns {MessageTrackingValue}
     */
    get messageTrackingValue() {
        return this.messaging && this.messaging.models['MessageTrackingValue'].get(this.props.localId);
    }

}

Object.assign(MessageTrackingValue, {
    props: { localId: String },
    template: "mail.MessageTrackingValue",
});

registerMessagingComponent(MessageTrackingValue);
