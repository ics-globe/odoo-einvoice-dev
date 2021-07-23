/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr, many2one, one2many, one2one } from '@discuss/model/model_field';
import { clear, create, link, replace, unlink, update } from '@discuss/model/model_field_command';

function factory(dependencies) {

    class Discuss extends dependencies['discuss.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {discuss.channel} channel
         */
        cancelChannelRenaming(channel) {
            this.update({ renamingChannels: unlink(channel) });
        }

        clearIsAddingItem() {
            this.update({
                addingChannelValue: "",
                isAddingChannel: false,
                isAddingChat: false,
            });
        }

        /**
         * Close the discuss app. Should reset its internal state.
         */
        close() {
            this.update({ isOpen: false });
        }

        focus() {
            this.update({ isDoFocus: true });
        }

        /**
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        async handleAddChannelAutocompleteSelect(ev, ui) {
            const name = this.addingChannelValue;
            this.clearIsAddingItem();
            if (ui.item.special) {
                const channel = await this.async(() =>
                    this.env.models['discuss.channel'].performRpcCreateChannel({
                        name,
                        privacy: ui.item.special,
                    })
                );
                channel.open();
            } else {
                const channel = await this.async(() =>
                    this.env.models['discuss.channel'].performRpcJoinChannel({
                        channelId: ui.item.id,
                    })
                );
                channel.open();
            }
        }

        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        async handleAddChannelAutocompleteSource(req, res) {
            const value = req.term;
            const escapedValue = owl.utils.escape(value);
            this.update({ addingChannelValue: value });
            const domain = [
                ['channel_type', '=', 'channel'],
                ['name', 'ilike', value],
            ];
            const fields = ['channel_type', 'name', 'public', 'uuid'];
            const result = await this.async(() => this.env.services.rpc({
                model: "discuss.channel",
                method: "search_read",
                kwargs: {
                    domain,
                    fields,
                },
            }));
            const items = result.map(data => {
                let escapedName = owl.utils.escape(data.name);
                return Object.assign(data, {
                    label: escapedName,
                    value: escapedName
                });
            });
            // XDU FIXME could use a component but be careful with owl's
            // renderToString https://github.com/odoo/owl/issues/708
            items.push({
                label: _.str.sprintf(
                    `<strong>${this.env._t('Create %s')}</strong>`,
                    `<em><span class="fa fa-hashtag"/>${escapedValue}</em>`,
                ),
                escapedValue,
                special: 'public'
            }, {
                label: _.str.sprintf(
                    `<strong>${this.env._t('Create %s')}</strong>`,
                    `<em><span class="fa fa-lock"/>${escapedValue}</em>`,
                ),
                escapedValue,
                special: 'private'
            });
            res(items);
        }

        /**
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        handleAddChatAutocompleteSelect(ev, ui) {
            this.env.messaging.openChat({ partnerId: ui.item.id });
            this.clearIsAddingItem();
        }

        /**
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        handleAddChatAutocompleteSource(req, res) {
            const value = owl.utils.escape(req.term);
            this.env.models['res.partner'].imSearch({
                callback: partners => {
                    const suggestions = partners.map(partner => {
                        return {
                            id: partner.id,
                            value: partner.nameOrDisplayName,
                            label: partner.nameOrDisplayName,
                        };
                    });
                    res(_.sortBy(suggestions, 'label'));
                },
                keyword: value,
                limit: 10,
            });
        }

        /**
         * Open channel from init active id. `initActiveId` is used to refer to
         * a channel that we may not have full data yet, such as when messaging
         * is not yet initialized.
         */
        openInitChannel() {
            const [model, id] = typeof this.initActiveId === 'number'
                ? ['discuss.channel', this.initActiveId]
                : this.initActiveId.split('_');
            const channel = this.env.models['discuss.channel'].findFromIdentifyingData({
                id: model !== 'discuss.box' ? Number(id) : id,
                model,
            });
            if (!channel) {
                return;
            }
            channel.open();
            if (this.env.messaging.device.isMobile && channel.channel_type) {
                this.update({ activeMobileNavbarTabId: channel.channel_type });
            }
        }


        /**
         * Opens the given channel in Discuss, and opens Discuss if necessary.
         *
         * @param {discuss.channel} channel
         */
        async openChannel(channel) {
            this.update({
                channel: link(channel),
            });
            this.focus();
            if (!this.isOpen) {
                this.env.bus.trigger('do-action', {
                    action: 'discuss.action_discuss',
                    options: {
                        active_id: this.channelToActiveId(this),
                        clear_breadcrumbs: false,
                        on_reverse_breadcrumb: () => this.close(), // this is useless, close is called by destroy anyway
                    },
                });
            }
        }

        /**
         * @param {discuss.channel} channel
         * @param {string} newName
         */
        async renameChannel(channel, newName) {
            await this.async(() => channel.rename(newName));
            this.update({ renamingChannels: unlink(channel) });
        }

        /**
         * @param {discuss.channel} channel
         */
        setChannelRenaming(channel) {
            this.update({ renamingChannels: link(channel) });
        }

        /**
         * @param {discuss.channel} channel
         * @returns {string}
         */
        channelToActiveId(channel) {
            return `discuss.channel_${channel.id}`;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeActiveId() {
            if (!this.channel) {
                return clear();
            }
            return this.channelToActiveId(this.channel);
        }

        /**
         * @private
         * @returns {string}
         */
        _computeAddingChannelValue() {
            if (!this.isOpen) {
                return "";
            }
            return this.addingChannelValue;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasChannelView() {
            if (!this.channel || !this.isOpen) {
                return false;
            }
            if (
                this.env.messaging.device.isMobile &&
                (
                    this.activeMobileNavbarTabId !== 'discussbox' ||
                    this.channel.model !== 'discuss.box'
                )
            ) {
                return false;
            }
            return true;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAddingChannel() {
            if (!this.isOpen) {
                return false;
            }
            return this.isAddingChannel;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAddingChat() {
            if (!this.isOpen) {
                return false;
            }
            return this.isAddingChat;
        }

        /**
         * Only pinned channel are allowed in discuss.
         *
         * @private
         * @returns {discuss.channel|undefined}
         */
        _computeChannel() {
            let channel = this.channel;
            if (this.env.messaging &&
                this.env.messaging.inbox &&
                this.env.messaging.device.isMobile &&
                this.activeMobileNavbarTabId === 'discussbox' &&
                this.initActiveId !== 'discuss.box_inbox' &&
                !channel
            ) {
                // After loading Discuss from an arbitrary tab other then 'discussbox',
                // switching to 'discussbox' requires to also set its inner-tab ;
                // by default the 'inbox'.
                return replace(this.env.messaging.inbox);
            }
            if (!channel || !channel.isPinned) {
                return unlink();
            }
            return;
        }

        /**
         * @private
         * @returns {discuss.channel_viewer}
         */
        _computeChannelViewer() {
            const channelViewerData = {
                hasChannelView: this.hasChannelView,
                stringifiedDomain: this.stringifiedDomain,
                channel: this.channel ? link(this.channel) : unlink(),
            };
            if (!this.channelViewer) {
                return create(channelViewerData);
            }
            return update(channelViewerData);
        }
    }

    Discuss.fields = {
        activeId: attr({
            compute: '_computeActiveId',
            dependencies: [
                'channel',
                'channelId',
            ],
        }),
        /**
         * Active mobile navbar tab, either 'discussbox', 'chat', or 'channel'.
         */
        activeMobileNavbarTabId: attr({
            default: 'discussbox',
        }),
        /**
         * Value that is used to create a channel from the sidebar.
         */
        addingChannelValue: attr({
            compute: '_computeAddingChannelValue',
            default: "",
            dependencies: ['isOpen'],
        }),
        /**
         * Serves as compute dependency.
         */
        device: one2one('discuss.device', {
            related: 'messaging.device',
        }),
        /**
         * Serves as compute dependency.
         */
        deviceIsMobile: attr({
            related: 'device.isMobile',
        }),
        /**
         * Determines whether `this.channel` should be displayed.
         */
        hasChannelView: attr({
            compute: '_computeHasChannelView',
            dependencies: [
                'activeMobileNavbarTabId',
                'deviceIsMobile',
                'isOpen',
                'channel',
            ],
        }),
        /**
         * Formatted init channel on opening discuss for the first time,
         * when no active channel is defined. Useful to set a channel to
         * open without knowing its local id in advance.
         * Support two formats:
         *    {string} discuss.channel_<channelId>
         *    {int} <channelId> with default model of 'discuss.channel'
         */
        initActiveId: attr({
            default: 'discuss.box_inbox',
        }),
        /**
         * Determine whether current user is currently adding a channel from
         * the sidebar.
         */
        isAddingChannel: attr({
            compute: '_computeIsAddingChannel',
            default: false,
            dependencies: ['isOpen'],
        }),
        /**
         * Determine whether current user is currently adding a chat from
         * the sidebar.
         */
        isAddingChat: attr({
            compute: '_computeIsAddingChat',
            default: false,
            dependencies: ['isOpen'],
        }),
        /**
         * Determine whether this discuss should be focused at next render.
         */
        isDoFocus: attr({
            default: false,
        }),
        /**
         * Whether the discuss app is open or not. Useful to determine
         * whether the discuss or chat window logic should be applied.
         */
        isOpen: attr({
            default: false,
        }),
        isChannelPinned: attr({
            related: 'channel.isPinned',
        }),
        /**
         * The menu_id of discuss app, received on discuss/init_messaging and
         * used to open discuss from elsewhere.
         */
        menu_id: attr({
            default: null,
        }),
        messaging: one2one('discuss.messaging', {
            inverse: 'discuss',
        }),
        renamingChannels: one2many('discuss.channel'),
        /**
         * Quick search input value in the discuss sidebar (desktop). Useful
         * to filter channels and chats based on this input content.
         */
        sidebarQuickSearchValue: attr({
            default: "",
        }),
        /**
         * Determines the domain to apply when fetching messages for `this.channel`.
         * This value should only be written by the control panel.
         */
        stringifiedDomain: attr({
            default: '[]',
        }),
        /**
         * Determines the `discuss.channel` that should be displayed by `this`.
         */
        channel: many2one('discuss.channel', {
            compute: '_computeChannel',
            dependencies: [
                'activeMobileNavbarTabId',
                'deviceIsMobile',
                'isChannelPinned',
                'messaging',
                'channel',
            ],
        }),
        channelId: attr({
            related: 'channel.id',
        }),
        /**
         * States the `discuss.channel_view` displaying `this.channel`.
         */
        channelView: one2one('discuss.channel_view', {
            related: 'channelViewer.channelView',
        }),
        /**
         * Determines the `discuss.channel_viewer` managing the display of `this.channel`.
         */
        channelViewer: one2one('discuss.channel_viewer', {
            compute: '_computeChannelViewer',
            dependencies: [
                'hasChannelView',
                'stringifiedDomain',
                'channel',
            ],
            isCausal: true,
            readonly: true,
            required: true,
        }),
    };

    Discuss.modelName = 'discuss.discuss';

    return Discuss;
}

registerNewModel('discuss.discuss', factory);
