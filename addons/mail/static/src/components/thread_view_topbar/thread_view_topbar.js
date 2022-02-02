/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model/use_update_to_model';

const { Component } = owl;

export class ThreadViewTopbar extends Component {

    /**
     * @override
     */
    setup() {
        useRefToModel({ fieldName: 'guestNameInputRef', modelName: 'ThreadViewTopbar', refName: 'guestNameInput' });
        useRefToModel({ fieldName: 'inviteButtonRef', modelName: 'ThreadViewTopbar', refName: 'inviteButton' });
        useRefToModel({ fieldName: 'threadNameInputRef', modelName: 'ThreadViewTopbar', refName: 'threadNameInput' });
        useRefToModel({ fieldName: 'threadDescriptionInputRef', modelName: 'ThreadViewTopbar', refName: 'threadDescriptionInput' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'ThreadViewTopbar' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ThreadViewTopbar}
     */
    get threadViewTopbar() {
        return this.messaging && this.messaging.models['ThreadViewTopbar'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickPhone(ev) {
        if (this.threadViewTopbar.thread.hasPendingRtcRequest) {
            return;
        }
        await this.threadViewTopbar.thread.toggleCall();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickCamera(ev) {
        if (this.threadViewTopbar.thread.hasPendingRtcRequest) {
            return;
        }
        await this.threadViewTopbar.thread.toggleCall({
            startWithVideo: true,
        });
    }

}

Object.assign(ThreadViewTopbar, {
    props: { localId: String },
    template: 'mail.ThreadViewTopbar',
});

registerMessagingComponent(ThreadViewTopbar);
