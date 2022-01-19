/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ModelRelationArrowView extends Component {

    /**
     * @returns {ModelRelationArrowView}
     */
    get modelRelationArrowView() {
        return this.messaging && this.messaging.models['ModelRelationArrowView'].get(this.props.localId);
    }

}

Object.assign(ModelRelationArrowView, {
    props: { localId: String },
    template: 'mail.ModelRelationArrowView',
});

registerMessagingComponent(ModelRelationArrowView);
