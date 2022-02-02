/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';

const { Component } = owl;

export class RtcLayoutMenu extends Component {

    /**
     * @override
     */
    setup() {
        useComponentToModel({ fieldName: 'component', modelName: 'RtcLayoutMenu' });
    }

    /**
     * @returns {RtcLayoutMenu}
     */
    get layoutMenu() {
        return this.messaging && this.messaging.models['RtcLayoutMenu'].get(this.props.localId);
    }

}

Object.assign(RtcLayoutMenu, {
    props: { localId: String },
    template: 'mail.RtcLayoutMenu',
});

registerMessagingComponent(RtcLayoutMenu);
