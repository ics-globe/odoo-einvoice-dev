/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2many, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace, link, replace} from '@mail/model/model_field_command';

import core from 'web.core';

const _t = core._t;

function factory(dependencies) {
    class Category extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        async close() {
            this.update({ isPendingOpen: false });
            await this.env.models['mail.category'].performRpcSetCategoryState({
                categoryType: this.type,
                isOpen: false,
            });
        }

        async open() {
            this.update({ isPendingOpen: true });
            await this.env.models['mail.category'].performRpcSetCategoryState({
                categoryType: this.type,
                isOpen: true,
            });
        }

        /**
         * Performs the `set_category_state` RPC on `mail.user.settings`.
         *
         * @static
         * @param {string} param0.categoryType
         * @param {boolean} param0.isOpen
         */
        static async performRpcSetCategoryState({ categoryType, isOpen }) {
            return this.env.services.rpc(
                {
                    model: 'mail.user.settings',
                    method: 'set_category_state',
                    kwargs: {
                        'category': categoryType,
                        'is_open': isOpen,
                    },
                },
                { shadow: true },
            );
        }

        async toggleIsOpen() {
            if(this.isOpen) {
                await this.close();
            } else {
                await this.open();
            }
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         * @returns {mail.category_item | undefined}
         */
        _computeActiveItem() {
            const thread = this.activeThread;
            if (thread && thread.channel_type === this.type){
                return insertAndReplace({ threadId: thread.id });
            } else {
                return clear();
            }

        }

        /**
         * @private
         * @returns {mail.category_item[]}
         */
        _computeCategoryItems(){
            let threads = this._sortThreads();
            if (this.sidebarSearchValue) {
                const qsVal = this.sidebarSearchValue.toLowerCase();
                threads = threads.filter(t => {
                    const nameVal = t.displayName.toLowerCase();
                    return nameVal.includes(qsVal);
                });
            }
            return insertAndReplace(threads.map(t => ({ threadId: t.id })));
        }

        /**
         * @private
         * @returns {integer}
         */
        _computeCounter() {
            switch (this.type) {
                case 'channel':
                    return this.selectedThreads.filter(thread => thread.message_needaction_counter > 0).length;
                case 'chat':
                    return this.selectedThreads.filter(thread => thread.localMessageUnreadCounter > 0).length;
                default:
                    return 0;
            }
        }

        /**
         * @private
         * @returns {string}
         */
        _computeDisplayName() {
            switch (this.type) {
                case 'channel':
                    return _t('Channels');
                case 'chat':
                    return _t('Direct Messages');
                default:
                    return '';
            }
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasAdd() {
            return this.isOpen && (this.type === 'chat' || this.type === 'channel');
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasView() {
            return this.type === 'channel';
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
        _computeSelectedThreads() {
            return replace(this.allPinnedChannels.filter(thread => thread.channel_type === this.type));
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsAddingItem() {
            return (this.type === 'channel' && this.isAddingChannel) ||
                (this.type === 'chat' && this.isAddingChat)
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

        /**
         * Sorts `selectedThreads` depending on the category type.
         *
         * @private
         * @returns {mail.thread[]}
         */
        _sortThreads() {
            switch (this.type) {
                case 'channel':
                    return this._sortByDisplayName();
                case 'chat':
                    return this._sortByLastActivityTime();
                default:
                    return this.selectedThreads;
            }
        }

        /**
         * Sorts `selectedThreads` by `displayName` in
         * case-insensitive alphabetical order.
         *
         * @private
         * @returns {mail.thread[]}
         */
        _sortByDisplayName() {
            return this.selectedThreads.sort((t1, t2) => {
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
         * Sorts `selectedThreads` by `lastActivityTime`.
         * The most recent one will come first.
         *
         * @private
         * @returns {mail.thread[]}
         */
        _sortByLastActivityTime() {
            return this.selectedThreads.sort((t1, t2) => {
                if(t1.lastActivityTime && !t2.lastActivityTime) {
                    return -1;
                } else if(!t1.lastActivityTime && t2.lastActivityTime) {
                    return 1;
                } else if(t1.lastActivityTime && t2.lastActivityTime && t1.lastActivityTime !== t2.lastActivityTime) {
                    return t2.lastActivityTime - t1.lastActivityTime;
                } else {
                    return t2.id - t1.id;
                }
            });

        }
    }

    Category.fields = {
        /**
         * The category item which is active and belongs
         * to the category.
         */
        activeItem: one2one('mail.category_item', {
            compute: '_computeActiveItem',
            dependencies: [
                'type',
                'activeThread',
            ],
        }),
        /**
         * The thread which is active in discuss.
         * Serves as compute dependency.
         */
        activeThread: one2one('mail.thread', {
            related: 'discuss.thread'
        }),
        /**
         * Serves as compute dependency.
         */
        allPinnedChannels: many2many('mail.thread', {
            related: 'messaging.allPinnedChannels'
        }),
        /**
         * Category items which belong to the category.
         * These items are sorted depending on the `type`
         * and filtered by `sidebarSearchValue`.
         */
        categoryItems: one2many('mail.category_item', {
            compute: '_computeCategoryItems',
            dependencies: [
                'selectedThreads',
                'selectedThreadsDisplayName',
                'selectedThreadsLastActivityTime',
                'sidebarSearchValue',
                'type',
            ],
        }),
        /**
         * The total amount unread/action-needed threads in the category.
         */
        counter: attr({
            compute: '_computeCounter',
            dependencies: [
                'selectedThreads',
                'selectedThreadsLocalMessageUnreadCounter',
                'selectedThreadsMessageNeedactionCounter',
                'type',
            ],
        }),
        discuss: many2one('mail.discuss', {
            related: 'messaging.discuss',
        }),
        displayName: attr({
            compute: '_computeDisplayName',
            dependencies: ['type'],
        }),
        /**
         * Boolean that determines whether this category has a 'add' command.
         */
        hasAdd: attr({
            compute: '_computeHasAdd',
            dependencies: [
                'type',
                'isOpen'
            ],
        }),
        /**
         * Boolean that determines whether this category has a 'view' command.
         */
        hasView: attr({
            compute: '_computeHasView',
            dependencies: ['type'],
        }),
        /**
         * Boolean that determines whether discuss is adding a new channel.
         * Used for computing `isAddingItem`.
         */
        isAddingChannel: attr({
            related: 'discuss.isAddingChannel',
        }),
        /**
         * Boolean that determines whether discuss is adding a new chat.
         * Used for computing `isAddingItem`.
         */
        isAddingChat: attr({
            related: 'discuss.isAddingChat',
        }),
        /**
         * Boolean that determines whether discuss is adding a new category item.
         */
        isAddingItem: attr({
            compute: '_computeIsAddingItem',
            dependencies: [
                'isAddingChannel',
                'isAddingChat',
                'type',
            ],
        }),
        /**
         * Boolean that determines whether this category is open.
         */
        isOpen: attr({
            compute: '_computeIsOpen',
            dependencies: [
                'isPendingOpen',
                'isServerOpen',
            ],
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
        isServerOpen: attr({
            default: true,
        }),
        messaging: many2one('mail.messaging', {
            compute: '_computeMessaging',
        }),
        /**
         * Not a real field, used to trigger `_onIsServerOpenChanged`.
         */
        onIsServerOpenChanged: attr({
            compute: '_onIsServerOpenChanged',
            dependencies: ['isServerOpen'],
            isOnChange: true,
        }),
        /**
         * Threads which belong to the category,
         * used for computing category items.
         */
        selectedThreads: one2many('mail.thread', {
            compute: '_computeSelectedThreads',
            dependencies: [
                'allPinnedChannels',
                'type',
            ]
        }),
        /**
         * Serves as compute dependency.
         */
        selectedThreadsDisplayName: attr({
            related: 'selectedThreads.displayName',
        }),
        /**
         * Serves as compute dependency.
         */
        selectedThreadsLastActivityTime: attr({
            related: 'selectedThreads.lastActivityTime',
        }),
        /**
         * Serves as compute dependency.
         */
        selectedThreadsLocalMessageUnreadCounter: attr({
            related: 'selectedThreads.localMessageUnreadCounter',
        }),
        /**
         * Serves as compute dependency.
         */
        selectedThreadsMessageNeedactionCounter: attr({
            related: 'selectedThreads.message_needaction_counter',
        }),
        /**
         * The value of discuss sidebar quick search input.
         * Serves as compute dependency.
         */
        sidebarSearchValue: attr({
            related: 'discuss.sidebarQuickSearchValue',
        }),
        type: attr({
            required: true,
        }),
    };

    Category.modelName = 'mail.category';

    return Category;
}

registerNewModel('mail.category', factory);
