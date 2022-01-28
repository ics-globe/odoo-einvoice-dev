/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';

const { Component } = owl;

export class DiscussSidebarCategory extends Component {

    /**
     * @override
     */
     setup() {
        super.setup();
        useRefToModel({ fieldName: 'inviteButtonRef', modelName: 'DiscussSidebarCategory', propNameAsRecordLocalId: 'categoryLocalId', refName: 'inviteButton' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {DiscussSidebarCategory}
     */
    get category() {
        return this.messaging.models['DiscussSidebarCategory'].get(this.props.localId);
    }
}

Object.assign(DiscussSidebarCategory, {
    props: { localId: String },
    template: 'mail.DiscussSidebarCategory',
});

registerMessagingComponent(DiscussSidebarCategory);
