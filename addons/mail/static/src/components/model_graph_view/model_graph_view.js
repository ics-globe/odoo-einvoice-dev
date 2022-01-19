/** @odoo-module **/

import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ModelGraphView extends Component {

    /**
     * @override
     */
    setup() {
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'ModelGraphView' });
    }

    /**
     * @returns {ModelGraphView}
     */
    get modelGraphView() {
        return this.messaging && this.messaging.models['ModelGraphView'].get(this.props.localId);
    }

}

Object.assign(ModelGraphView, {
    props: { localId: String },
    template: 'mail.ModelGraphView',
});

registerMessagingComponent(ModelGraphView);
