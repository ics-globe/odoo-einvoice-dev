/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr, many2many, many2one } from '@discuss/model/model_field';
import { clear, link, replace } from '@discuss/model/model_field_command';
import emojis from '@discuss/js/emojis';
import { addLink, parseAndTransform, timeFromNow } from '@discuss/js/utils';

import { str_to_datetime } from 'web.time';

function factory(dependencies) {

    class DiscussChannelMessage extends dependencies['discuss.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Mark all messages of current user with given domain as read.
         *
         * @static
         * @param {Array[]} domain
         */
        static async markAllAsRead(domain) {
            await this.env.services.rpc({
                model: 'discuss.channel.message',
                method: 'mark_all_as_read',
                kwargs: { domain },
            });
        }

        /**
         * Mark provided messages as read. Messages that have been marked as
         * read are acknowledged by server with response as longpolling
         * notification of following format:
         *
         * [[dbname, 'res.partner', partnerId], { type: 'mark_as_read' }]
         *
         * @see discuss.messaging_notification_handler:_handleNotificationPartnerMarkAsRead()
         *
         * @static
         * @param {discuss.channel.message[]} messages
         */
        static async markAsRead(messages) {
            await this.env.services.rpc({
                model: 'discuss.channel.message',
                method: 'set_message_done',
                args: [messages.map(message => message.id)]
            });
        }

        /**
         * Performs the `message_fetch` RPC on `discuss.channel.message`.
         *
         * @static
         * @param {Array[]} domain
         * @param {integer} [limit]
         * @param {Object} [context]
         * @returns {discuss.channel.message[]}
         */
        static async performRpcMessageFetch(domain, limit, context) {
            const messagesData = await this.env.services.rpc({
                model: 'discuss.channel.message',
                method: 'message_fetch',
                kwargs: {
                    context,
                    domain,
                    limit,
                },
            }, { shadow: true });
            const messages = this.env.models['discuss.channel.message'].insert(messagesData);
            // compute seen indicators (if applicable)
            for (const message of messages) {
                this.env.models['discuss.message_seen_indicator'].insert({
                    channelId: message.channel.id,
                    messageId: message.id,
                });
            }
            return messages;
        }

        /**
         * Unstar all starred messages of current user.
         */
        static async unstarAll() {
            await this.env.services.rpc({
                model: 'discuss.channel.message',
                method: 'unstar_all',
            });
        }

        /**
         * Mark this message as read, so that it no longer appears in current
         * partner Inbox.
         */
        async markAsRead() {
            await this.async(() => this.env.services.rpc({
                model: 'discuss.channel.message',
                method: 'set_message_done',
                args: [[this.id]]
            }));
        }

        /**
         * Refreshes the value of `dateFromNow` field to the "current now".
         */
        refreshDateFromNow() {
            this.update({ dateFromNow: this._computeDateFromNow() });
        }

        /**
         * Action to initiate reply to current message in Discuss Inbox. Assumes
         * that Discuss and Inbox are already opened.
         */
        replyTo() {
            this.env.messaging.discuss.replyToMessage(this);
        }

        /**
         * Toggle the starred status of the provided message.
         */
        async toggleStar() {
            await this.async(() => this.env.services.rpc({
                model: 'discuss.channel.message',
                method: 'toggle_message_starred',
                args: [[this.id]]
            }));
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
         * @returns {string}
         */
        _computeDateFromNow() {
            if (!this.date) {
                return clear();
            }
            return timeFromNow(moment(str_to_datetime(this.date)));
        }

        /**
         * @returns {boolean}
         */
        _computeFailureNotifications() {
            return replace(this.notifications.filter(notifications =>
                ['exception', 'bounce'].includes(notifications.notification_status)
            ));
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentPartnerAuthor() {
            return !!(
                this.author &&
                this.messagingCurrentPartner &&
                this.messagingCurrentPartner === this.author
            );
        }

        /**
         * The method does not attempt to cover all possible cases of empty
         * messages, but mostly those that happen with a standard flow. Indeed
         * it is preferable to be defensive and show an empty message sometimes
         * instead of hiding a non-empty message.
         *
         * The main use case for when a message should become empty is for a
         * message posted with only an attachment (no body) and then the
         * attachment is deleted.
         *
         * The main use case for being defensive with the check is when
         * receiving a message that has no textual content but has other
         * meaningful HTML tags (eg. just an <img/>).
         *
         * @private
         * @returns {boolean}
         */
        _computeIsEmpty() {
            const isBodyEmpty = (
                !this.body ||
                [
                    '',
                    '<p></p>',
                    '<p><br></p>',
                    '<p><br/></p>',
                ].includes(this.body.replace(/\s/g, ''))
            );
            return (
                isBodyEmpty &&
                this.attachments.length === 0
            );
        }

        /**
         * @private
         * @returns {discuss.messaging}
         */
        _computeMessaging() {
            return link(this.env.messaging);
        }

        /**
         * This value is meant to be based on field body which is
         * returned by the server (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the message has been created
         * directly from user input and not from server data as it's not escaped.
         *
         * @private
         * @returns {string}
         */
        _computePrettyBody() {
            let prettyBody;
            for (const emoji of emojis) {
                const { unicode } = emoji;
                const regexp = new RegExp(
                    `(?:^|\\s|<[a-z]*>)(${unicode})(?=\\s|$|</[a-z]*>)`,
                    "g"
                );
                const originalBody = this.body;
                prettyBody = this.body.replace(
                    regexp,
                    ` <span class="o-discuss-emoji">${unicode}</span> `
                );
                // Idiot-proof limit. If the user had the amazing idea of
                // copy-pasting thousands of emojis, the image rendering can lead
                // to memory overflow errors on some browsers (e.g. Chrome). Set an
                // arbitrary limit to 200 from which we simply don't replace them
                // (anyway, they are already replaced by the unicode counterpart).
                if (_.str.count(prettyBody, "o-discuss-emoji") > 200) {
                    prettyBody = originalBody;
                }
            }
            // add anchor tags to urls
            return parseAndTransform(prettyBody, addLink);
        }

    }

    DiscussChannelMessage.fields = {
        attachments: many2many('ir.attachment', {
            inverse: 'discussChannelMessages',
        }),
        author: many2one('res.partner', {
            inverse: 'discussChannelMessagesAsAuthor',
        }),
        /**
         * This value is meant to be returned by the server
         * (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the message has been created
         * directly from user input and not from server data as it's not escaped.
         */
        body: attr({
            default: "",
        }),
        /**
         * States the channel on which this message belongs.
         */
        channel: many2one('discuss.channel', {
            inverse: 'messages',
            readonly: true,
            required: true,
        }),
        /**
         * Determines the date of the message as a string.
         */
        date: attr(),
        /**
         * States the time elapsed since date up to now.
         */
        dateFromNow: attr({
            compute: '_computeDateFromNow',
            dependencies: [
                'date',
            ],
        }),
        id: attr({
            required: true,
        }),
        isCurrentPartnerAuthor: attr({
            compute: '_computeIsCurrentPartnerAuthor',
            default: false,
            dependencies: [
                'author',
                'messagingCurrentPartner',
            ],
        }),
        /**
         * Determine whether the message has to be considered empty or not.
         *
         * An empty message has no text, no attachment and no tracking value.
         */
        isEmpty: attr({
            compute: '_computeIsEmpty',
            dependencies: [
                'attachments',
                'body',
            ],
        }),
        is_discussion: attr({
            default: false,
        }),
        /**
         * Determine whether the current partner is mentioned.
         */
        isCurrentPartnerMentioned: attr({
            default: false,
        }),
        message_type: attr(),
        messaging: many2one('discuss.messaging', {
            compute: '_computeMessaging',
        }),
        messagingCurrentPartner: many2one('res.partner', {
            related: 'messaging.currentPartner',
        }),
        /**
         * This value is meant to be based on field body which is
         * returned by the server (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the message has been created
         * directly from user input and not from server data as it's not escaped.
         */
        prettyBody: attr({
            compute: '_computePrettyBody',
            dependencies: ['body'],
        }),
    };

    DiscussChannelMessage.modelName = 'discuss.channel.message';

    return DiscussChannelMessage;
}

registerNewModel('discuss.channel.message', factory);
