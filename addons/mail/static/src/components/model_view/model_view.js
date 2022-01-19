/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ModelView extends Component {

    /**
     * @override
     */
    setup() {
        useComponentToModel({ fieldName: 'component', modelName: 'ModelView' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'ModelView' });
    }

    /**
     * @returns {ModelView}
     */
    get modelView() {
        return this.messaging && this.messaging.models['ModelView'].get(this.props.localId);
    }

}

Object.assign(ModelView, {
    props: { localId: String },
    template: 'mail.ModelView',
});

registerMessagingComponent(ModelView);
