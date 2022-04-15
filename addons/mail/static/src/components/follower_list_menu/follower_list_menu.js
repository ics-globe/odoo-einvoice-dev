/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { isEventHandled } from '@mail/utils/utils';

const { Component, onMounted, onWillUnmount, useRef } = owl;

export class FollowerListMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this._dropdownRef = useRef('dropdown');
        this._onHideFollowerListMenu = this._onHideFollowerListMenu.bind(this);
        this._onClickCaptureGlobal = this._onClickCaptureGlobal.bind(this);
        onMounted(() => this._mounted());
        onWillUnmount(() => this._willUnmount());
    }

    _mounted() {
        document.addEventListener('click', this._onClickCaptureGlobal, true);
    }

    _willUnmount() {
        document.removeEventListener('click', this._onClickCaptureGlobal, true);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {FollowerListMenuView}
     */
    get followerListMenuView() {
        return this.props.record;
    }

    /**
     * @return {Thread}
     */
    get thread() {
        return this.props.thread;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAddFollowers(ev) {
        ev.preventDefault();
        this.followerListMenuView.hide();
        this.thread.promptAddPartnerFollower();
    }

    /**
     * Close the dropdown when clicking outside of it.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCaptureGlobal(ev) {
        // since dropdown is conditionally shown based on state, dropdownRef can be null
        if (this._dropdownRef.el && !this._dropdownRef.el.contains(ev.target)) {
            this.followerListMenuView.hide();
        }
    }

<<<<<<< HEAD
=======
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickFollowersButton(ev) {
        this.state.isDropdownOpen = !this.state.isDropdownOpen;
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickFollower(ev) {
        if (isEventHandled(ev, 'Follower.clickRemove')) {
            return;
        }
        this._hide();
    }

    /**
     * @private
     */
    _onHideFollowerListMenu() {
        this._hide();
    }
>>>>>>> 05aa96bb648... temp
}

Object.assign(FollowerListMenu, {
    defaultProps: {
        isChatterButton: false,
    },
    props: {
<<<<<<< HEAD
        thread: Object,
=======
        isDisabled: { type: Boolean, optional: true },
        chatterLocalId: {
            type: String,
            optional: true,
        },
        threadLocalId: String,
>>>>>>> 05aa96bb648... temp
        isChatterButton: { type: Boolean, optional: true },
        record: Object,
    },
    template: 'mail.FollowerListMenu',
});

registerMessagingComponent(FollowerListMenu);
