/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr, one2one } from '@discuss/model/model_field';
import { unlink } from '@discuss/model/model_field_command';

function factory(dependencies) {

    class ResUsers extends dependencies['discuss.model'] {

        /**
         * @override
         */
        _willDelete() {
            if (this.env.messaging) {
                if (this === this.env.messaging.currentUser) {
                    this.env.messaging.update({ currentUser: unlink() });
                }
            }
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Performs the `read` RPC on `res.users`.
         *
         * @static
         * @param {Object} param0
         * @param {Object} param0.context
         * @param {string[]} param0.fields
         * @param {integer[]} param0.ids
         */
        static async performRpcRead({ context, fields, ids }) {
            const usersData = await this.env.services.rpc({
                model: 'res.users',
                method: 'read',
                args: [ids],
                kwargs: {
                    context,
                    fields,
                },
            }, { shadow: true });
            return this.env.models['res.users'].insert(usersData);
        }

        /**
         * Fetches the partner of this user.
         */
        async fetchPartner() {
            return this.env.models['res.users'].performRpcRead({
                ids: [this.id],
                fields: ['partner_id'],
                context: { active_test: false },
            });
        }

        /**
         * Gets the chat between this user and the current user.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @returns {discuss.channel|undefined}
         */
        async getChat() {
            if (!this.partner) {
                await this.async(() => this.fetchPartner());
            }
            if (!this.partner) {
                // This user has been deleted from the server or never existed:
                // - Validity of id is not verified at insert.
                // - There is no bus notification in case of user delete from
                //   another tab or by another user.
                this.env.services['notification'].notify({
                    message: this.env._t("You can only chat with existing users."),
                    type: 'warning',
                });
                return;
            }
            // in other cases a chat would be valid, find it or try to create it
            let chat = this.env.models['discuss.channel'].find(channel =>
                channel.channel_type === 'chat' &&
                channel.correspondent === this.partner &&
                channel.model === 'discuss.channel' &&
                channel.public === 'private'
            );
            if (!chat ||!chat.isPinned) {
                // if chat is not pinned then it has to be pinned client-side
                // and server-side, which is a side effect of following rpc
                chat = await this.async(() =>
                    this.env.models['discuss.channel'].performRpcCreateChat({
                        partnerIds: [this.partner.id],
                    })
                );
            }
            if (!chat) {
                this.env.services['notification'].notify({
                    message: this.env._t("An unexpected error occurred during the creation of the chat."),
                    type: 'warning',
                });
                return;
            }
            return chat;
        }

        /**
         * Opens a chat between this user and the current user and returns it.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @param {Object} [options] forwarded to @see `discuss.channel:open()`
         * @returns {discuss.channel|undefined}
         */
        async openChat(options) {
            const chat = await this.async(() => this.getChat());
            if (!chat) {
                return;
            }
            await this.async(() => chat.open(options));
            return chat;
        }

        /**
         * Opens the most appropriate view that is a profile for this user.
         * Because user is a rather technical model to allow login, it's the
         * partner profile that contains the most useful information.
         *
         * @override
         */
        async openProfile() {
            if (!this.partner) {
                await this.async(() => this.fetchPartner());
            }
            if (!this.partner) {
                // This user has been deleted from the server or never existed:
                // - Validity of id is not verified at insert.
                // - There is no bus notification in case of user delete from
                //   another tab or by another user.
                this.env.services['notification'].notify({
                    message: this.env._t("You can only open the profile of existing users."),
                    type: 'warning',
                });
                return;
            }
            return this.partner.openProfile();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeDisplayName() {
            return this.display_name || this.partner && this.partner.display_name;
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeNameOrDisplayName() {
            return this.partner && this.partner.nameOrDisplayName || this.display_name;
        }
    }

    ResUsers.fields = {
        id: attr({
            required: true,
        }),
        /**
         * Determines whether this user is an internal user. An internal user is
         * a member of the group `base.group_user`. This is the inverse of the
         * `share` field in python.
         */
        isInternalUser: attr(),
        display_name: attr({
            compute: '_computeDisplayName',
            dependencies: [
                'display_name',
                'partnerDisplayName',
            ],
        }),
        model: attr({
            default: 'res.user',
        }),
        nameOrDisplayName: attr({
            compute: '_computeNameOrDisplayName',
            dependencies: [
                'display_name',
                'partnerNameOrDisplayName',
            ]
        }),
        partner: one2one('res.partner', {
            inverse: 'user',
        }),
        /**
         * Serves as compute dependency.
         */
        partnerDisplayName: attr({
            related: 'partner.display_name',
        }),
        /**
         * Serves as compute dependency.
         */
        partnerNameOrDisplayName: attr({
            related: 'partner.nameOrDisplayName',
        }),
    };

    ResUsers.modelName = 'res.users';

    return ResUsers;
}

registerNewModel('res.users', factory);
