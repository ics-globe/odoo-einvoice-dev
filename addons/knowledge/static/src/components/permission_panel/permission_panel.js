/** @odoo-module **/

import session from 'web.session';
import Dialog from 'web.Dialog';
import { _t } from 'web.core';
import { useService } from '@web/core/utils/hooks';

const { Component, onWillStart, useState } = owl;
const permissionLevel = {'none': 0, 'read': 1, 'write': 2}
const restrictMessage = _t("Are you sure you want to restrict this role and restrict access ? "
+ "This article will no longer inherit access settings from the parent page.");
const looseWriteMessage = _t('Are you sure you want to remove you own "Write" access ?');

class PermissionPanel extends Component {
    /**
     * @override
     */
    setup () {
        super.setup();
        this.rpc = useService('rpc');
        this.state = useState({
            loading: true,
            partner_id: session.partner_id
        })
        onWillStart(this.loadPanel);
    }

    async loadPanel () {
        const data = await this.loadData();
        this.state = {
            ...this.state,
            ...data,
            loading: false
        };
        this.render();
        this._showPanel();
    }

    /**
     * @returns {Object}
     */
    async loadData () {
        return await this.rpc({
            route: '/knowledge/get_article_permission_panel_data',
            params: {
                article_id: this.props.article_id
            }
        });
    }

    /**
     * @returns {Array[Array]}
     */
    getInternalPermissionOptions () {
        return this.state.internal_permission_options;
    }

    /**
     * @param {Proxy} member
     * @returns {Boolean}
     */
    isLoggedUser (member) {
        return member.partner_id === session.partner_id;
    }

    /**
     * Opens the article with the given id
     * @param {integer} id
     */
    openArticle (id) {
        this.env.bus.trigger('do-action', {
            action: 'knowledge.ir_actions_server_knowledge_home_page',
            options: {
                additional_context: {
                    res_id: id
                }
            }
        });
    }

    /**
     * Callback function called when the internal permission of the article changes.
     * @param {Event} event
     */
    _onChangeInternalPermission (event) {
        const $select = $(event.target);
        const index = this.state.members.findIndex(current => {
            return current.partner_id === session.partner_id;
        });
        if (index < 0) {
            return;
        }
        const newPermission = $select.val();
        const oldPermission = this.state.internal_permission;
        const willRestrict = this.state.based_on && permissionLevel[newPermission] < permissionLevel[oldPermission]
                                && permissionLevel[newPermission] < permissionLevel[this.state.parent_permission];
        const willLooseAccess = $select.val() === 'none' && (index >= 0 && this.state.members[index].permission === 'none');
        const confirm = () => {
            this.rpc({
                route: '/knowledge/article/set_internal_permission',
                params: {
                    article_id: this.props.article_id,
                    permission: newPermission,
                }
            }).then(res => {
                if (this._onChangedPermission(res, willLooseAccess)) {
                    this.loadPanel();
                }
            });
        };

        if (!willLooseAccess && !willRestrict) {
            confirm();
            return;
        }

        const discard = () => {
            $select.val(oldPermission);
            this.loadPanel();
        };
        const looseAccessMessage = _t('Are you sure you want to set the internal permission to "none" ? If you do, you will no longer have access to the article.');
        this._showConfirmDialog(willLooseAccess ? looseAccessMessage : restrictMessage, confirm, discard);
    }

    /**
     * Callback function called when the permission of a user changes.
     * @param {Event} event
     * @param {Proxy} member
     */
    _onChangeMemberPermission (event, member) {
        const index = this.state.members.indexOf(member);
        if (index < 0) {
            return;
        }
        const $select = $(event.target);
        const newPermission = $select.val();
        const oldPermission = member.permission;
        const willLooseAccess = this.isLoggedUser(member) && newPermission === 'none';
        const willRestrict = this.state.based_on && permissionLevel[newPermission] < permissionLevel[oldPermission];
        const willLooseWrite = this.isLoggedUser(member) && newPermission !== 'write' && oldPermission === 'write';
        const confirm = () => {
            this.rpc({
                route: '/knowledge/article/set_member_permission',
                params: {
                    article_id: this.props.article_id,
                    permission: newPermission,
                    member_id: member.based_on ? false : member.id,
                    inherited_member_id: member.based_on ? member.id: false,
                }
            }).then(res => {
                const reloadArticleId = willLooseWrite && !willLooseAccess ? this.props.article_id : false;
                if (this._onChangedPermission(res, willLooseAccess||willLooseWrite, reloadArticleId)) {
                    this.loadPanel();
                }
            });
        };

        if (!willLooseAccess && !willRestrict && !willLooseWrite) {
            confirm();
            return;
        }

        const discard = () => {
            $select.val(this.state.members[index].permission);
            this.loadPanel();
        };
        const looseAccessMessage = _t('Are you sure you want to set your permission to "none"? If you do, you will no longer have access to the article.');
        const message = willLooseAccess ? looseAccessMessage : willLooseWrite ? looseWriteMessage : looseAccessMessage;
        this._showConfirmDialog(message, confirm, discard);
    }

    /**
     * @param {Event} event
     * @param {integer} id - article id
     */
    _onOpen (event, id) {
        event.preventDefault();
        this.openArticle(id);
    }

    /**
     * Callback function called when a member is removed.
     * @param {Event} event
     * @param {Proxy} member
     */
    _onRemoveMember (event, member) {
        if (!this.state.members.includes(member)) {
            return;
        }
        const willRestrict = member.based_on ? true : false;
        const willLooseAccess = this.isLoggedUser(member);
        const confirm = () => {
            this.rpc({
                route: '/knowledge/article/remove_member',
                params: {
                    article_id: this.props.article_id,
                    member_id: member.based_on ? false : member.id,
                    inherited_member_id: member.based_on ? member.id: false,
                }
            }).then(res => {
                if (this._onChangedPermission(res, willLooseAccess)) {
                    this.loadPanel();
                }
            });
        };

        if (!willLooseAccess && !willRestrict) {
            confirm();
            return;
        }

        const looseAccessMessage = _t('Are you sure you want to leave this article? If you do, you will no longer have access to the article.');
        const message = willLooseAccess ? looseAccessMessage : restrictMessage;
        const discard = () => {
            this.loadPanel();
        };
        this._showConfirmDialog(message, confirm, discard);
    }

    /**
     * Callback function called when user clicks on 'Restore' button.
     * @param {Event} event
     */
    _onRestore (event) {
        const articleId = this.props.article_id;
        const confirm = () => {
            this.rpc({
                model: 'knowledge.article',
                method: 'restore_article_access',
                args: [[articleId]],
            }).then(res => {
                if (res) {
                    if (this._onChangedPermission({success: res})) {
                        this.loadPanel();
                    }
                }
            });
        };

        const message = _t('Are you sure you want to restore access?');
        this._showConfirmDialog(message, confirm);
    }

    /**
     * @param {Event} event
     * @param {Proxy} member
     */
    async _onMemberAvatarClick (event, member) {
        if (!member.partner_share) {
            const partnerRead = await this.rpc({
                model: 'res.partner',
                method: 'read',
                args: [member.partner_id, ['user_ids']],
            });
            const userIds = partnerRead && partnerRead.length === 1 ? partnerRead[0]['user_ids'] : false;
            const userId = userIds && userIds.length === 1 ? userIds[0] : false;

            if (userId) {
                const messaging = await Component.env.services.messaging.get();
                messaging.openChat({
                    userId: userId
                });
            }
        }
    }

  /**
    * This method is called before each permission change rpc when the user needs to confirm the change as them
    * would loose them access to the article if them do confirm.
    * @param {str} message
    * @param {function} confirm
    * @param {function} discard
    */
    _showConfirmDialog (message, confirm, discard) {
        if (discard === undefined) {
            discard = this.loadPanel;
        }
        Dialog.confirm(this, message, {
            buttons: [{
                text: _t('confirm'),
                classes: 'btn-primary',
                close: true,
                click: confirm
            }, {
                text: _t('Discard'),
                close: true,
                click: discard
            }],
        });
    }

  /**
    * This method is called after each permission change rpc.
    * It will check if a reloading of the article tree or a complete reload is needed in function
    * of the new article state (if change of category or if user lost his own access to the current article).
    * return True if the caller should continue after executing this method, and False, if caller should stop.
    * @param {Dict} result
    * @param {Boolean} lostAccess
    */
    _onChangedPermission (result, reloadAll, reloadArticleId) {
        if (result.error) {
            Dialog.alert(this, result.error,{
              title: _t("Error"),
            });
        } else if (reloadAll && reloadArticleId) {  // Loose write access
            this.openArticle(reloadArticleId);
            return false;
        } else if (reloadAll) {  // Loose access -> Hard Reload
            window.location.replace('/knowledge/home');
        } else if (result.reload_tree) {
            this.env.bus.trigger('reload_tree', {});
        }
        return true;
    }

    _showPanel () {
        // TODO DBE: get permission panel with owl brol ??
        const $permissionPanel = $('.o_knowledge_share_panel');
        $permissionPanel.addClass('show');
        $permissionPanel.parent().addClass('show');
    }
}

PermissionPanel.template = 'knowledge.PermissionPanel';
PermissionPanel.props = [
    'article_id',
    'user_permission'
];

export default PermissionPanel;
