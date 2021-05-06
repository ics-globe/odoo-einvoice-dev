/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import EditableText from '@mail/components/editable_text/editable_text';
import PartnerImStatusIcon from '@mail/components/partner_im_status_icon/partner_im_status_icon';
import ThreadIcon from '@mail/components/thread_icon/thread_icon';

import { isEventHandled } from '@mail/utils/utils';

import Dialog from 'web.Dialog';

const { Component } = owl;

const components = { EditableText, PartnerImStatusIcon, ThreadIcon }

class CategoryItem extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const categoryItem = this.env.models['mail.category_item'].get(props.categoryItemLocalId);
            const correspondent = categoryItem ? categoryItem.correspondent : undefined;
            return {
                categoryItem: categoryItem && categoryItem.__state,
                correspondentName: correspondent && correspondent.name,
            }
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.category_item}
     */
    get categoryItem() {
        return this.env.models['mail.category_item'].get(this.props.categoryItemLocalId);
    }

    /**
     * @returns {mail.discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.discuss;
    }

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.categoryItem && this.categoryItem.thread;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Promise}
     */
     _askAdminConfirmation() {
        return new Promise(resolve => {
            Dialog.confirm(this,
                this.env._t("You are the administrator of this channel. Are you sure you want to leave?"),
                {
                    buttons: [
                        {
                            text: this.env._t("Leave"),
                            classes: 'btn-primary',
                            close: true,
                            click: resolve
                        },
                        {
                            text: this.env._t("Discard"),
                            close: true
                        }
                    ]
                }
            );
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
     _onCancelRenaming(ev) {
        this.discuss.cancelThreadRenaming(this.thread);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
     _onClick(ev) {
        if (isEventHandled(ev, 'EditableText.click')) {
            return;
        }
        this.thread.open();
    }

    /**
     * Stop propagation to prevent selecting this item.
     *
     * @private
     * @param {CustomEvent} ev
     */
     _onClickedEditableText(ev) {
        ev.stopPropagation();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
     async _onClickLeave(ev) {
        ev.stopPropagation();
        if (this.thread.creator === this.env.messaging.currentUser) {
            await this._askAdminConfirmation();
        }
        this.thread.unsubscribe();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRename(ev) {
        ev.stopPropagation();
        this.discuss.setThreadRenaming(this.thread);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
     _onClickSettings(ev) {
        ev.stopPropagation();
        return this.env.bus.trigger('do-action', {
            action: {
                type: 'ir.actions.act_window',
                res_model: this.thread.model,
                res_id: this.thread.id,
                views: [[false, 'form']],
                target: 'current'
            },
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
     _onClickUnpin(ev) {
        ev.stopPropagation();
        this.thread.unsubscribe();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.newName
     */
    _onValidateEditableText(ev) {
        ev.stopPropagation();
        this.discuss.renameThread(this.thread, ev.detail.newName);
    }

}

Object.assign(CategoryItem, {
    components,
    props: {
        categoryItemLocalId: String,
    },
    template: 'mail.CategoryItem',
});

export default CategoryItem;
