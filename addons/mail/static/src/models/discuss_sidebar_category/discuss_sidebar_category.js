/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2many, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace, link, replace } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

function factory(dependencies) {
    class DiscussSidebarCategory extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Performs the `set_mail_user_settings` RPC on `mail.user.settings`.
         *
         * @static
         * @param {Object.<string, boolean>} mailUserSettings
         */
        static async performRpcSetMailUserSettings(mailUserSettings) {
            return this.env.services.rpc(
                {
                    model: 'mail.user.settings',
                    method: 'set_mail_user_settings',
                    args: [[this.env.messaging.mailUserSettingsId]],
                    kwargs: {
                        new_settings: mailUserSettings,
                    },
                },
                { shadow: true },
            );
        }

        /**
         * Closes the category and notity server to change the state
         */
        async close() {
            this.update({ isPendingOpen: false });
            await this.env.models['mail.discuss_sidebar_category'].performRpcSetMailUserSettings({
                [this.serverStateKey]: false,
            });
        }

        /**
         * Opens the category and notity server to change the state
         */
        async open() {
            this.update({ isPendingOpen: true });
            await this.env.models['mail.discuss_sidebar_category'].performRpcSetMailUserSettings({
                [this.serverStateKey]: true,
            });
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         * @returns {mail.discuss_sidebar_category_item | undefined}
         */
        _computeActiveItem() {
            const thread = this.env.messaging.discuss.thread;
            if (thread && this.supportedChannelTypes.includes(thread.channel_type)) {
                return insertAndReplace({ channelId: thread.id });
            }
            return clear();
        }

        /**
         * @private
         * @returns {mail.discuss_sidebar_category_item[]}
         */
        _computeCategoryItems() {
            let channels = this.selectedSortedChannels;
            const searchValue = this.env.messaging.discuss.sidebarQuickSearchValue;
            if (searchValue) {
                const qsVal = searchValue.toLowerCase();
                channels = channels.filter(t => {
                    const nameVal = t.displayName.toLowerCase();
                    return nameVal.includes(qsVal);
                });
            }
            return insertAndReplace(channels.map(c => ({ channelId: c.id })));
        }

        /**
         * @private
         * @returns {integer}
         */
        _computeCounter() {
            switch (this.counterComputeMethod) {
                case 'needaction':
                    return this.selectedChannels.filter(thread => thread.message_needaction_counter > 0).length;
                case 'unread':
                    return this.selectedChannels.filter(thread => thread.localMessageUnreadCounter > 0).length;
            }
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsOpen() {
            return this.isPendingOpen !== undefined ? this.isPendingOpen : this.isServerOpen;
        }

        /**
         * @private
         * @returns {mail.messaging}
         */
        _computeMessaging() {
            return link(this.env.messaging);
        }

        /**
         * @private
         * @returns {mail.thread[]}
         */
        _computeSelectedChannels() {
            return replace(this.env.models['mail.thread'].all(thread =>
                thread.model === 'mail.channel' &&
                thread.isPinned &&
                this.supportedChannelTypes.includes(thread.channel_type))
            );
        }

        /**
         *
         * @private
         * @returns {mail.thread[]}
         */
        _computeSelectedSortedChannels() {
            switch (this.sortComputeMethod) {
                case 'name':
                    return replace(this._sortByDisplayName());
                case 'last_action':
                    return replace(this._sortByLastMeaningfulActionTime());
            }
        }

        /**
         * Sorts `selectedChannels` by `displayName` in
         * case-insensitive alphabetical order.
         *
         * @private
         * @returns {mail.thread[]}
         */
        _sortByDisplayName() {
            return this.selectedChannels.sort((t1, t2) => {
                if (t1.displayName && !t2.displayName) {
                    return -1;
                } else if (!t1.displayName && t2.displayName) {
                    return 1;
                } else if (t1.displayName && t2.displayName && t1.displayName !== t2.displayName) {
                    return t1.displayName.toLowerCase() < t2.displayName.toLowerCase() ? -1 : 1;
                } else {
                    return t1.id - t2.id;
                }
            });
        }

        /**
         * Sorts `selectedChannels` by `lastMeaningfulActionTime`.
         * The most recent one will come first.
         *
         * @private
         * @returns {mail.thread[]}
         */
        _sortByLastMeaningfulActionTime() {
            return this.selectedChannels.sort((t1, t2) => {
                if (t1.lastMeaningfulActionTime && !t2.lastMeaningfulActionTime) {
                    return -1;
                } else if (!t1.lastMeaningfulActionTime && t2.lastMeaningfulActionTime) {
                    return 1;
                } else if (t1.lastMeaningfulActionTime && t2.lastMeaningfulActionTime && t1.lastMeaningfulActionTime !== t2.lastMeaningfulActionTime) {
                    return t2.lastMeaningfulActionTime - t1.lastMeaningfulActionTime;
                } else {
                    return t2.id - t1.id;
                }
            });
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Changes the category open states when clicked.
         *
         * @private
         */
        async _onClick() {
            if (this.isOpen) {
                await this.close();
            } else {
                await this.open();
            }
        }

        /**
         * @private
         * @param {Event} ev
         * @param {Object} ui
         * @param {Object} ui.item
         * @param {integer} ui.item.id
         */
        _onAddItemAutocompleteSelect(ev, ui) {
            switch (this.autocompleteMethod) {
                case 'channel':
                    this.env.messaging.discuss.handleAddChannelAutocompleteSelect(ev, ui);
                    break;
                case 'chat':
                    this.env.messaging.discuss.handleAddChatAutocompleteSelect(ev, ui);
                    break;
            }
        }

        /**
         * @private
         * @param {Object} req
         * @param {string} req.term
         * @param {function} res
         */
        _onAddItemAutocompleteSource(req, res) {
            switch (this.autocompleteMethod) {
                case 'channel':
                    this.env.messaging.discuss.handleAddChannelAutocompleteSource(req, res);
                    break;
                case 'chat':
                    this.env.messaging.discuss.handleAddChatAutocompleteSource(req, res);
                    break;
            }
        }

        /**
         * Redirects to the public channels window when view command is clicked.
         *
         * @private
         */
        _onClickViewCommand() {
            return this.env.bus.trigger('do-action', {
                action: {
                    name: this.env._t("Public Channels"),
                    type: 'ir.actions.act_window',
                    res_model: 'mail.channel',
                    views: [[false, 'kanban'], [false, 'form']],
                    domain: [['public', '!=', 'private']],
                },
            });
        }

        /**
         * Handles change of open state coming from the server. Useful to
         * clear pending state once server acknowledged the change.
         *
         * @private
         */
        _onIsServerOpenChanged() {
            if (this.isServerOpen === this.isPendingOpen) {
                this.update({ isPendingOpen: clear() });
            }
        }
    }

    DiscussSidebarCategory.fields = {
        /**
         * The category item which is active and belongs
         * to the category.
         */
        activeItem: one2one('mail.discuss_sidebar_category_item', {
            compute: '_computeActiveItem',
        }),
        /**
         * Determines how the autocomplete of this category should behave.
         * Must be one of: 'channel', 'chat'.
         */
        autocompleteMethod: attr(),
        /**
         * The title text in UI for command `add`
         */
        commandAddTitleText: attr(),
        /**
         * The sorted category items which belong to the category.
         * These items are also filtered by `sidebarQuickSearchValue`.
         */
        categoryItems: one2many('mail.discuss_sidebar_category_item', {
            compute: '_computeCategoryItems',
        }),
        /**
         * The total amount unread/action-needed threads in the category.
         */
        counter: attr({
            compute: '_computeCounter',
        }),
        /**
         * Determines how the counter of this category should be computed.
         * Supported methods: 'needaction', 'unread'.
         */
        counterComputeMethod: attr({
            required: true,
        }),
        /**
         * Display name of the category.
         */
        displayName: attr(),
        /**
         * Boolean that determines whether this category has a 'add' command.
         */
        hasAddCommand: attr({
            default: false,
        }),
        /**
         * Boolean that determines whether this category has a 'view' command.
         */
        hasViewCommand: attr({
            default: false,
        }),
        /**
         * Boolean that determines whether discuss is adding a new category item.
         */
        isAddingItem: attr({
            default: false,
        }),
        /**
         * Boolean that determines whether this category is open.
         */
        isOpen: attr({
            compute: '_computeIsOpen',
        }),
        /**
         * Boolean that determines if there is a pending open state change,
         * which is requested by the client but not yet confirmed by the server.
         *
         * This field can be updated to immediately change the open state on the
         * interface and to notify the server of the new state.
         */
        isPendingOpen: attr(),
        /**
         * Boolean that determines the last open state known by the server.
         */
        isServerOpen: attr(),
        messaging: many2one('mail.messaging', {
            compute: '_computeMessaging',
        }),
        /**
         * The placeholder text used when a new item is being added in UI.
         */
        newItemPlaceholderText: attr(),
        /**
         * Channels which belong to the category,
         */
        selectedChannels: one2many('mail.thread', {
            compute: '_computeSelectedChannels',
        }),
        /**
         * Channels which belongs to the category,
         * and sorted based on the `supported_channel_type`.
         */
        selectedSortedChannels: one2many('mail.thread', {
            compute: '_computeSelectedSortedChannels',
        }),
        /**
         * The key used in the server side for the category state
         */
        serverStateKey: attr(),
        /**
         * Determines the sorting method of channels in this category.
         * Must be one of: 'name', 'last_action'.
         */
        sortComputeMethod: attr({
            required: true,
        }),
        /**
         * Channel type which is supported by the category.
         */
        supportedChannelTypes: attr({
            required: true,
            readonly: true,
        }),
    };
    DiscussSidebarCategory.onChanges = [
        new OnChange({
            dependencies: ['isServerOpen'],
            methodName: ['_onIsServerOpenChanged'],
        }),
    ];
    DiscussSidebarCategory.modelName = 'mail.discuss_sidebar_category';

    return DiscussSidebarCategory;
}

registerNewModel('mail.discuss_sidebar_category', factory);
