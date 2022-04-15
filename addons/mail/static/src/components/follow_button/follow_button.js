/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class FollowButton extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
<<<<<<< HEAD
     * @return {FollowButtonView}
=======
     * @return {Thread}
     */
    get thread() {
        return this.messaging && this.messaging.models['Thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickFollow(ev) {
        this.thread.follow();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickUnfollow(ev) {
        await this.thread.unfollow();
        if (this.props.chatterLocalId) {
            const chatter = this.messaging.models['Chatter'].get(this.props.chatterLocalId);
            if (chatter) {
                chatter.reloadParentView({ fieldNames: ['message_follower_ids'] });
            }
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onMouseLeaveUnfollow(ev) {
        this.state.isUnfollowButtonHighlighted = false;
    }

    /**
     * @private
     * @param {MouseEvent} ev
>>>>>>> 05aa96bb648... temp
     */
    get followButtonView() {
        return this.props.record;
    }

}

Object.assign(FollowButton, {
<<<<<<< HEAD
    props: { record: Object },
=======
    defaultProps: {
        isDisabled: false,
        isChatterButton: false,
    },
    props: {
        isDisabled: { type: Boolean, optional: true },
        chatterLocalId: {
            type: String,
            optional: true,
        },
        threadLocalId: String,
        isChatterButton: { type: Boolean, optional: true },
    },
>>>>>>> 05aa96bb648... temp
    template: 'mail.FollowButton',
});

registerMessagingComponent(FollowButton);
