/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr, many2one, one2many, one2one } from '@discuss/model/model_field';
import { insert, link } from '@discuss/model/model_field_command';
import { cleanSearchTerm } from '@discuss/utils/utils';

function factory(dependencies) {

    class ResPartner extends dependencies['discuss.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Fetches partners matching the given search term to extend the
         * JS knowledge and to update the suggestion list accordingly.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {discuss.channel} [options.channel] prioritize and/or restrict
         *  result in the context of given channel
         */
        static async fetchSuggestions(searchTerm, { channel } = {}) {
            const kwargs = { search: searchTerm };
            const isNonPublicChannel = channel && channel.public !== 'public';
            if (isNonPublicChannel) {
                kwargs.channel_id = channel.id;
            }
            const suggestedPartners = await this.env.services.rpc(
                {
                    model: 'res.partner',
                    method: 'get_mention_suggestions',
                    kwargs,
                },
                { shadow: true },
            );
            const partners = this.env.models['res.partner'].insert(suggestedPartners);
            if (isNonPublicChannel) {
                channel.update({ members: link(partners) });
            }
        }

        /**
         * Search for partners matching `keyword`.
         *
         * @static
         * @param {Object} param0
         * @param {function} param0.callback
         * @param {string} param0.keyword
         * @param {integer} [param0.limit=10]
         */
        static async imSearch({ callback, keyword, limit = 10 }) {
            // prefetched partners
            let partners = [];
            const cleanedSearchTerm = cleanSearchTerm(keyword);
            const currentPartner = this.env.messaging.currentPartner;
            for (const partner of this.all(partner => partner.active)) {
                if (partners.length < limit) {
                    if (
                        partner !== currentPartner &&
                        partner.name &&
                        partner.user &&
                        cleanSearchTerm(partner.name).includes(cleanedSearchTerm)
                    ) {
                        partners.push(partner);
                    }
                }
            }
            if (!partners.length) {
                const partnersData = await this.env.services.rpc(
                    {
                        model: 'res.partner',
                        method: 'im_search',
                        args: [keyword, limit]
                    },
                    { shadow: true }
                );
                const newPartners = this.insert(partnersData);
                partners.push(...newPartners);
            }
            callback(partners);
        }

        /**
         * Returns partners that match the given search term.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {discuss.channel} [options.channel] prioritize and/or restrict
         *  result in the context of given channel
         * @returns {[res.partner[], res.partner[]]}
         */
        static searchSuggestions(searchTerm, { channel } = {}) {
            let partners;
            const isNonPublicChannel = channel && channel.model === 'discuss.channel' && channel.public !== 'public';
            if (isNonPublicChannel) {
                // Only return the channel members when in the context of a
                // non-public channel. Indeed, the message with the mention
                // would be notified to the mentioned partner, so this prevents
                // from inadvertently leaking the private message to the
                // mentioned partner.
                partners = channel.members;
            } else {
                partners = this.env.models['res.partner'].all();
            }
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            const mainSuggestionList = [];
            const extraSuggestionList = [];
            for (const partner of partners) {
                if (
                    (!partner.active && partner !== this.env.messaging.partnerRoot) ||
                    partner.id <= 0 ||
                    this.env.messaging.publicPartners.includes(partner)
                ) {
                    // ignore archived partners (except OdooBot), temporary
                    // partners (livechat guests), public partners (technical)
                    continue;
                }
                if (
                    (partner.nameOrDisplayName && cleanSearchTerm(partner.nameOrDisplayName).includes(cleanedSearchTerm)) ||
                    (partner.email && cleanSearchTerm(partner.email).includes(cleanedSearchTerm))
                ) {
                    if (partner.user) {
                        mainSuggestionList.push(partner);
                    } else {
                        extraSuggestionList.push(partner);
                    }
                }
            }
            return [mainSuggestionList, extraSuggestionList];
        }

        /**
         * @static
         */
        static async startLoopFetchImStatus() {
            await this._fetchImStatus();
            this._loopFetchImStatus();
        }

        /**
         * Checks whether this partner has a related user and links them if
         * applicable.
         */
        async checkIsUser() {
            const userIds = await this.async(() => this.env.services.rpc({
                model: 'res.users',
                method: 'search',
                args: [[['partner_id', '=', this.id]]],
                kwargs: {
                    context: { active_test: false },
                },
            }, { shadow: true }));
            this.update({ hasCheckedUser: true });
            if (userIds.length > 0) {
                this.update({ user: insert({ id: userIds[0] }) });
            }
        }

        /**
         * Gets the chat between the user of this partner and the current user.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @returns {discuss.channel|undefined}
         */
        async getChat() {
            if (!this.user && !this.hasCheckedUser) {
                await this.async(() => this.checkIsUser());
            }
            // prevent chatting with non-users
            if (!this.user) {
                this.env.services['notification'].notify({
                    message: this.env._t("You can only chat with partners that have a dedicated user."),
                    type: 'info',
                });
                return;
            }
            return this.user.getChat();
        }

        /**
         * Returns the text that identifies this partner in a mention.
         *
         * @returns {string}
         */
        getMentionText() {
            return this.name;
        }

        /**
         * Returns a sort function to determine the order of display of partners
         * in the suggestion list.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {discuss.channel} [options.channel] prioritize result in the
         *  context of given channel
         * @returns {function}
         */
        static getSuggestionSortFunction(searchTerm, { channel } = {}) {
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            return (a, b) => {
                const isAInternalUser = a.user && a.user.isInternalUser;
                const isBInternalUser = b.user && b.user.isInternalUser;
                if (isAInternalUser && !isBInternalUser) {
                    return -1;
                }
                if (!isAInternalUser && isBInternalUser) {
                    return 1;
                }
                if (channel && channel.model === 'discuss.channel') {
                    const isAMember = channel.members.includes(a);
                    const isBMember = channel.members.includes(b);
                    if (isAMember && !isBMember) {
                        return -1;
                    }
                    if (!isAMember && isBMember) {
                        return 1;
                    }
                }
                if (channel) {
                    const isAFollower = channel.followersPartner.includes(a);
                    const isBFollower = channel.followersPartner.includes(b);
                    if (isAFollower && !isBFollower) {
                        return -1;
                    }
                    if (!isAFollower && isBFollower) {
                        return 1;
                    }
                }
                const cleanedAName = cleanSearchTerm(a.nameOrDisplayName || '');
                const cleanedBName = cleanSearchTerm(b.nameOrDisplayName || '');
                if (cleanedAName.startsWith(cleanedSearchTerm) && !cleanedBName.startsWith(cleanedSearchTerm)) {
                    return -1;
                }
                if (!cleanedAName.startsWith(cleanedSearchTerm) && cleanedBName.startsWith(cleanedSearchTerm)) {
                    return 1;
                }
                if (cleanedAName < cleanedBName) {
                    return -1;
                }
                if (cleanedAName > cleanedBName) {
                    return 1;
                }
                const cleanedAEmail = cleanSearchTerm(a.email || '');
                const cleanedBEmail = cleanSearchTerm(b.email || '');
                if (cleanedAEmail.startsWith(cleanedSearchTerm) && !cleanedAEmail.startsWith(cleanedSearchTerm)) {
                    return -1;
                }
                if (!cleanedBEmail.startsWith(cleanedSearchTerm) && cleanedBEmail.startsWith(cleanedSearchTerm)) {
                    return 1;
                }
                if (cleanedAEmail < cleanedBEmail) {
                    return -1;
                }
                if (cleanedAEmail > cleanedBEmail) {
                    return 1;
                }
                return a.id - b.id;
            };
        }

        /**
         * Opens a chat between the user of this partner and the current user
         * and returns it.
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
         * Opens the most appropriate view that is a profile for this partner.
         */
        async openProfile() {
            return this.env.messaging.openDocument({
                id: this.id,
                model: 'res.partner',
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeAvatarUrl() {
            if (this === this.env.messaging.partnerRoot) {
                return '/discuss/static/src/img/odoobot.png';
            }
            return `/web/image/res.partner/${this.id}/avatar_128`;
        }

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

        /**
         * @static
         * @private
         */
        static async _fetchImStatus() {
            const partnerIds = [];
            for (const partner of this.all()) {
                if (partner.im_status !== 'im_partner' && partner.id > 0) {
                    partnerIds.push(partner.id);
                }
            }
            if (partnerIds.length === 0) {
                return;
            }
            const dataList = await this.env.services.rpc({
                route: '/longpolling/im_status',
                params: {
                    partner_ids: partnerIds,
                },
            }, { shadow: true });
            this.insert(dataList);
        }

        /**
         * @static
         * @private
         */
        static _loopFetchImStatus() {
            setTimeout(async () => {
                await this._fetchImStatus();
                this._loopFetchImStatus();
            }, 50 * 1000);
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeDisplayName() {
            return this.display_name || this.user && this.user.display_name;
        }

        /**
         * @private
         * @returns {discuss.messaging}
         */
        _computeMessaging() {
            return link(this.env.messaging);
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeNameOrDisplayName() {
            return this.name || this.display_name;
        }

    }

    ResPartner.fields = {
        active: attr({
            default: true,
        }),
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
            dependencies: [
                'id',
                'messagingPartnerRoot',
            ],
        }),
        country: many2one('res.country'),
        display_name: attr({
            compute: '_computeDisplayName',
            default: "",
            dependencies: [
                'display_name',
                'userDisplayName',
            ],
        }),
        email: attr(),
        // TODO SEB move into mail
        // failureNotifications: one2many('mail.notification', {
        //     related: 'messagesAsAuthor.failureNotifications',
        // }),
        /**
         * Whether an attempt was already made to fetch the user corresponding
         * to this partner. This prevents doing the same RPC multiple times.
         */
        hasCheckedUser: attr({
            default: false,
        }),
        id: attr({
            required: true,
        }),
        im_status: attr(),
        discussChannelMessagesAsAuthor: one2many('discuss.channel.message', {
            inverse: 'author',
        }),
        /**
         * Serves as compute dependency.
         */
        messaging: many2one('discuss.messaging', {
            compute: '_computeMessaging',
        }),
        messagingPartnerRoot: many2one('res.partner', {
            related: 'messaging.partnerRoot',
        }),
        model: attr({
            default: 'res.partner',
        }),
        name: attr(),
        nameOrDisplayName: attr({
            compute: '_computeNameOrDisplayName',
            dependencies: [
                'display_name',
                'name',
            ],
        }),
        user: one2one('res.users', {
            inverse: 'partner',
        }),
        /**
         * Serves as compute dependency.
         */
        userDisplayName: attr({
            related: 'user.display_name',
        }),
    };

    ResPartner.modelName = 'res.partner';

    return ResPartner;
}

registerNewModel('res.partner', factory);
