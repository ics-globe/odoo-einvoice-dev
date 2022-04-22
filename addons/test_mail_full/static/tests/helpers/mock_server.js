/** @odoo-module **/

import '@mail/../tests/helpers/mock_server'; // ensure mail overrides are applied first

import MockServer from 'web.MockServer';

MockServer.include({
    //--------------------------------------------------------------------------
    // Private Mocked Routes
    //--------------------------------------------------------------------------

    /**
     * Simulates `message_format` on `mail.message`.
     *
     * @override
     * @returns {Object[]}
     */
    _mockMailMessageMessageFormat(ids) {
        const messageFormat = this._super(...arguments);
        for (const formatter of messageFormat) {
            const [rating] = this._getRecords('rating.rating', [
                ['message_id', '=', formatter.id],
            ]);
            if (rating) {
                formatter['rating'] = [['insert-and-replace', {
                    'id': rating.id,
                    'ratingImageUrl': rating.rating_image_url,
                    'ratingText': rating.rating_text,
                }]]
            }
        }
        return messageFormat;
    },
});
