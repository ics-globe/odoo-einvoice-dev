/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, link, unlink } from '@mail/model/model_field_command';
import { markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'ChatWindow',
    identifyingFields: ['manager', ['thread', 'managerAsNewMessage']],
    recordMethods: {
        /**
         * Close this chat window.
         *
         * @param {Object} [param0={}]
         * @param {boolean} [param0.notifyServer]
         */
        close({ notifyServer } = {}) {
            if (notifyServer === undefined) {
                notifyServer = !this.messaging.device.isMobile;
            }
            if (this.messaging.device.isMobile && !this.messaging.discuss.discussView) {
                // If we are in mobile and discuss is not open, it means the
                // chat window was opened from the messaging menu. In that
                // case it should be re-opened to simulate it was always
                // there in the background.
                this.messaging.messagingMenu.update({ isOpen: true });
            }
            // Flux specific: 'closed' fold state should only be saved on the
            // server when manually closing the chat window. Delete at destroy
            // or sync from server value for example should not save the value.
            if (this.thread && notifyServer && !this.messaging.currentGuest) {
                this.thread.notifyFoldStateToServer('closed');
            }
            if (this.exists()) {
                this.delete();
            }
        },
        expand() {
            if (this.thread) {
                this.thread.open({ expanded: true });
            }
        },
        /**
         * Programmatically auto-focus an existing chat window.
         */
        focus() {
            if (this.newMessageFormInputView) {
                this.newMessageFormInputView.update({ doFocus: true });
            }
            if (this.threadView && this.threadView.composerView) {
                this.threadView.composerView.update({ doFocus: true });
            }
        },
        focusNextVisibleUnfoldedChatWindow() {
            const nextVisibleUnfoldedChatWindow = this._getNextVisibleUnfoldedChatWindow();
            if (nextVisibleUnfoldedChatWindow) {
                nextVisibleUnfoldedChatWindow.focus();
            }
        },
        focusPreviousVisibleUnfoldedChatWindow() {
            const previousVisibleUnfoldedChatWindow =
                this._getNextVisibleUnfoldedChatWindow({ reverse: true });
            if (previousVisibleUnfoldedChatWindow) {
                previousVisibleUnfoldedChatWindow.focus();
            }
        },
        /**
         * @param {Object} [param0={}]
         * @param {boolean} [param0.notifyServer]
         */
        fold({ notifyServer } = {}) {
            if (notifyServer === undefined) {
                notifyServer = !this.messaging.device.isMobile;
            }
            this.update({ isFolded: true });
            // Flux specific: manually folding the chat window should save the
            // new state on the server.
            if (this.thread && notifyServer && !this.messaging.currentGuest) {
                this.thread.notifyFoldStateToServer('folded');
            }
        },
        /**
         * Makes this chat window active, which consists of making it visible,
         * unfolding it, and focusing it if the user isn't on a mobile device.
         *
         * @param {Object} [options]
         */
        makeActive(options) {
            this.makeVisible();
            this.unfold(options);
            if ((options && options.focus !== undefined) ? options.focus : !this.messaging.device.isMobileDevice) {
                this.focus();
            }
        },
        /**
         * Makes this chat window visible by swapping it with the last visible
         * chat window, or do nothing if it is already visible.
         */
        makeVisible() {
            if (this.isVisible) {
                return;
            }
            const lastVisible = this.manager.lastVisible;
            this.manager.swap(this, lastVisible);
        },
        /**
         * Handles click on the "stop adding users" button.
         *
         * @param {MouseEvent} ev
         */
        onClickHideInviteForm(ev) {
            markEventHandled(ev, 'ChatWindow.onClickCommand');
            this.update({ channelInvitationForm: clear() });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickHideMemberList(ev) {
            markEventHandled(ev, 'ChatWindow.onClickHideMemberList');
            this.update({ isMemberListOpened: false });
            if (this.threadViewer.threadView) {
                this.threadViewer.threadView.addComponentHint('member-list-hidden');
            }
        },
        /**
         * Handles click on the "add users" button.
         *
         * @param {MouseEvent} ev
         */
        onClickShowInviteForm(ev) {
            markEventHandled(ev, 'ChatWindow.onClickCommand');
            this.update({
                channelInvitationForm: insertAndReplace({
                    doFocusOnSearchInput: true,
                }),
                isMemberListOpened: false,
            });
            if (!this.messaging.isCurrentUserGuest) {
                this.channelInvitationForm.searchPartnersToInvite();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickShowMemberList(ev) {
            markEventHandled(ev, 'ChatWindow.onClickShowMemberList');
            this.update({
                channelInvitationForm: clear(),
                isMemberListOpened: true,
            });
        },
        /**
         * Swap this chat window with the previous one.
         */
        shiftPrev() {
            this.manager.shiftPrev(this);
        },
        /**
         * Swap this chat window with the next one.
         */
        shiftNext() {
            this.manager.shiftNext(this);
        },
        /**
         * @param {Object} [param0={}]
         * @param {boolean} [param0.notifyServer]
         */
        unfold({ notifyServer } = {}) {
            if (notifyServer === undefined) {
                notifyServer = !this.messaging.device.isMobile;
            }
            this.update({ isFolded: false });
            // Flux specific: manually opening the chat window should save the
            // new state on the server.
            if (this.thread && notifyServer && !this.messaging.currentGuest) {
                this.thread.notifyFoldStateToServer('open');
            }
        },
        /**
          * @private
          * @returns {string}
          */
        _computeComponentStyle() {
            const textDirection = this.messaging.locale.textDirection;
            const offsetFrom = textDirection === 'rtl' ? 'left' : 'right';
            const oppositeFrom = offsetFrom === 'right' ? 'left' : 'right';
            return `${offsetFrom}: ${this.visibleOffset}px; ${oppositeFrom}: auto`;
        },
        /**
         * @private
         * @returns {string}
         */
        _computeComponentStyle() {
            const textDirection = this.messaging.locale.textDirection;
            const offsetFrom = textDirection === 'rtl' ? 'left' : 'right';
            const oppositeFrom = offsetFrom === 'right' ? 'left' : 'right';
            return `${offsetFrom}: ${this.visibleOffset}px; ${oppositeFrom}: auto`;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasCallButtons() {
            return Boolean(this.thread) && this.thread.rtcSessions.length === 0 && ['channel', 'chat', 'group'].includes(this.thread.channel_type);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasInviteFeature() {
            return Boolean(
                this.thread && this.thread.hasInviteFeature &&
                this.messaging && this.messaging.device && this.messaging.device.isMobile
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasShiftPrev() {
            if (!this.manager) {
                return false;
            }
            const allVisible = this.manager.allOrderedVisible;
            const index = allVisible.findIndex(visible => visible === this);
            if (index === -1) {
                return false;
            }
            return index < allVisible.length - 1;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasShiftNext() {
            if (!this.manager) {
                return false;
            }
            const index = this.manager.allOrderedVisible.findIndex(visible => visible === this);
            if (index === -1) {
                return false;
            }
            return index > 0;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasThreadView() {
            return this.isVisible && !this.isFolded && !!this.thread && !this.isMemberListOpened && !this.channelInvitationForm;
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeIsFocused() {
            if (this.newMessageFormInputView && this.newMessageFormInputView.isFocused) {
                return true;
            }
            if (this.threadView && this.threadView.isComposerFocused) {
                return true;
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsFolded() {
            const thread = this.thread;
            if (thread) {
                return thread.foldState === 'folded';
            }
            return this.isFolded;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsVisible() {
            if (!this.manager) {
                return false;
            }
            return this.manager.allOrderedVisible.includes(this);
        },
        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            if (this.thread) {
                return this.thread.displayName;
            }
            return this.env._t("New message");
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeNewMessageFormInputView() {
            if (this.isVisible && !this.isFolded && !this.thread) {
                return insertAndReplace();
            }
            return clear();
        },
        /**
         * @private
         * @returns {ThreadViewer}
         */
        _computeThreadViewer() {
            return insertAndReplace({
                compact: true,
                hasThreadView: this.hasThreadView,
                thread: this.thread ? link(this.thread) : unlink(),
            });
        },
        /**
         * @private
         * @returns {integer|undefined}
         */
        _computeVisibleIndex() {
            if (!this.manager) {
                return clear();
            }
            const visible = this.manager.visual.visible;
            const index = visible.findIndex(visible => visible.chatWindowLocalId === this.localId);
            if (index === -1) {
                return clear();
            }
            return index;
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeVisibleOffset() {
            if (!this.manager) {
                return 0;
            }
            const visible = this.manager.visual.visible;
            const index = visible.findIndex(visible => visible.chatWindowLocalId === this.localId);
            if (index === -1) {
                return 0;
            }
            return visible[index].offset;
        },
        /**
         * Cycles to the next possible visible and unfolded chat window starting
         * from the `currentChatWindow`, following the natural order based on the
         * current text direction, and with the possibility to `reverse` based on
         * the given parameter.
         *
         * @private
         * @param {Object} [param0={}]
         * @param {boolean} [param0.reverse=false]
         * @returns {ChatWindow|undefined}
         */
        _getNextVisibleUnfoldedChatWindow({ reverse = false } = {}) {
            const orderedVisible = this.manager.allOrderedVisible;
            /**
             * Return index of next visible chat window of a given visible chat
             * window index. The direction of "next" chat window depends on
             * `reverse` option.
             *
             * @param {integer} index
             * @returns {integer}
             */
            const _getNextIndex = index => {
                const directionOffset = reverse ? 1 : -1;
                let nextIndex = index + directionOffset;
                if (nextIndex > orderedVisible.length - 1) {
                    nextIndex = 0;
                }
                if (nextIndex < 0) {
                    nextIndex = orderedVisible.length - 1;
                }
                return nextIndex;
            };

            const currentIndex = orderedVisible.findIndex(visible => visible === this);
            let nextIndex = _getNextIndex(currentIndex);
            let nextToFocus = orderedVisible[nextIndex];
            while (nextToFocus.isFolded) {
                nextIndex = _getNextIndex(nextIndex);
                nextToFocus = orderedVisible[nextIndex];
            }
            return nextToFocus;
        },
    },
    fields: {
        /**
         * Determines the channel invitation form displayed by this chat window
         * (if any). Only makes sense if hasInviteFeature is true.
         */
        channelInvitationForm: one('ChannelInvitationForm', {
            inverse: 'chatWindow',
            isCausal: true,
        }),
        componentStyle: attr({
            compute: '_computeComponentStyle',
        }),
        /**
         * States the OWL component of this chat window.
         */
        component: attr(),
        /**
         * Determines whether the buttons to start a RTC call should be displayed.
         */
        hasCallButtons: attr({
            default: false,
            compute: '_computeHasCallButtons',
        }),
        /**
         * States whether this chat window has the invite feature.
         */
        hasInviteFeature: attr({
            compute: '_computeHasInviteFeature',
        }),
        hasShiftPrev: attr({
            compute: '_computeHasShiftPrev',
            default: false,
        }),
        hasShiftNext: attr({
            compute: '_computeHasShiftNext',
            default: false,
        }),
        /**
         * Determines whether `this.thread` should be displayed.
         */
        hasThreadView: attr({
            compute: '_computeHasThreadView',
        }),
        /**
         * States whether `this` is focused. Useful for visual clue.
         */
        isFocused: attr({
            compute: '_computeIsFocused',
            default: false,
        }),
        /**
         * Determines whether `this` is folded.
         */
        isFolded: attr({
            default: false,
        }),
        /**
         * Determines whether the member list of this chat window is opened.
         * Only makes sense if this thread hasMemberListFeature is true.
         */
        isMemberListOpened: attr({
            default: false,
        }),
        /**
         * States whether `this` is visible or not. Should be considered
         * read-only. Setting this value manually will not make it visible.
         * @see `makeVisible`
         */
        isVisible: attr({
            compute: '_computeIsVisible',
        }),
        manager: one('ChatWindowManager', {
            inverse: 'chatWindows',
            readonly: true,
        }),
        managerAsNewMessage: one('ChatWindowManager', {
            inverse: 'newMessageChatWindow',
            readonly: true,
        }),
        name: attr({
            compute: '_computeName',
        }),
        newMessageFormInputView: one('AutocompleteInputView', {
            compute: '_computeNewMessageFormInputView',
            inverse: 'chatWindowOwnerAsNewMessageFormInput',
            isCausal: true,
        }),
        /**
         * Determines the `Thread` that should be displayed by `this`.
         * If no `Thread` is linked, `this` is considered "new message".
         */
        thread: one('Thread', {
            inverse: 'chatWindow',
            readonly: true,
        }),
        /**
         * States the `ThreadView` displaying `this.thread`.
         */
        threadView: one('ThreadView', {
            related: 'threadViewer.threadView',
        }),
        /**
         * Determines the `ThreadViewer` managing the display of `this.thread`.
         */
        threadViewer: one('ThreadViewer', {
            compute: '_computeThreadViewer',
            inverse: 'chatWindow',
            isCausal: true,
            readonly: true,
            required: true,
        }),
        /**
         * This field handle the "order" (index) of the visible chatWindow inside the UI.
         *
         * Using LTR, the right-most chat window has index 0, and the number is incrementing from right to left.
         * Using RTL, the left-most chat window has index 0, and the number is incrementing from left to right.
         */
        visibleIndex: attr({
            compute: '_computeVisibleIndex',
        }),
        visibleOffset: attr({
            compute: '_computeVisibleOffset',
        }),
    },
});
