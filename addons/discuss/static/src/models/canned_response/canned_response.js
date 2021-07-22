/** @odoo-module **/

import { registerNewModel } from '@discuss/model/model_core';
import { attr } from '@discuss/model/model_field';
import { cleanSearchTerm } from '@discuss/utils/utils';

function factory(dependencies) {

    class DiscussCannedResponse extends dependencies['discuss.model'] {

        /**
         * Fetches canned responses matching the given search term to extend the
         * JS knowledge and to update the suggestion list accordingly.
         *
         * In practice all canned responses are already fetched at init so this
         * method does nothing.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {discuss.channel} [options.channel] prioritize and/or restrict
         *  result in the context of given channel
         */
        static fetchSuggestions(searchTerm, { channel } = {}) {}

        /**
         * Returns a sort function to determine the order of display of canned
         * responses in the suggestion list.
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
                const cleanedAName = cleanSearchTerm(a.source || '');
                const cleanedBName = cleanSearchTerm(b.source || '');
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
                return a.id - b.id;
            };
        }

        /*
         * Returns canned responses that match the given search term.
         *
         * @static
         * @param {string} searchTerm
         * @param {Object} [options={}]
         * @param {discuss.channel} [options.channel] prioritize and/or restrict
         *  result in the context of given channel
         * @returns {[discuss.canned_response[], discuss.canned_response[]]}
         */
        static searchSuggestions(searchTerm, { channel } = {}) {
            const cleanedSearchTerm = cleanSearchTerm(searchTerm);
            return [this.env.messaging.cannedResponses.filter(cannedResponse =>
                cleanSearchTerm(cannedResponse.source).includes(cleanedSearchTerm)
            )];
        }

        /**
         * Returns the text that identifies this canned response in a mention.
         *
         * @returns {string}
         */
        getMentionText() {
            return this.substitution;
        }

    }

    DiscussCannedResponse.fields = {
        id: attr(),
        /**
         *  The keyword to use a specific canned response.
         */
        source: attr(),
        /**
         * The canned response itself which will replace the keyword previously
         * entered.
         */
        substitution: attr(),
    };

    DiscussCannedResponse.modelName = 'discuss.canned_response';

    return DiscussCannedResponse;
}

registerNewModel('discuss.canned_response', factory);
