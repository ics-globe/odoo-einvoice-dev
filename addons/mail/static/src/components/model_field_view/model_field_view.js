/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ModelFieldView extends Component {

    /**
     * @override
     */
    setup() {
        useComponentToModel({ fieldName: 'component', modelName: 'ModelFieldView' });
        useRefToModel({ fieldName: 'nameRef', modelName: 'ModelFieldView', refName: 'name' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'ModelFieldView' });
    }

    /**
     * @returns {ModelFieldView}
     */
    get modelFieldView() {
        return this.messaging && this.messaging.models['ModelFieldView'].get(this.props.localId);
    }

}

Object.assign(ModelFieldView, {
    props: { localId: String },
    template: 'mail.ModelFieldView',
});

registerMessagingComponent(ModelFieldView);
