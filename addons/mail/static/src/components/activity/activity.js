/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Popover from "web.Popover";
import { LegacyComponent } from "@web/legacy/legacy_component";

export class Activity extends LegacyComponent {

    /**
     * @override
     */
     setup() {
        super.setup();
        useComponentToModel({ fieldName: 'ActivityView/component', modelName: 'ActivityView' });
    }

    /**
     * @returns {ActivityView}
     */
    get activityView() {
        return this.messaging && this.messaging.models['ActivityView'].get(this.props.localId);
    }

    get(name) {
        return this.activityView.get(name);
    }

}

Object.assign(Activity, {
    props: { localId: String },
    template: 'mail.Activity',
    components: { Popover },
});

registerMessagingComponent(Activity);
