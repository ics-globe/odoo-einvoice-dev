/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure the model definition is loaded before the patch
import '@mail/models/thread_preview_view';

patchRecordMethods('ThreadPreviewView', {
    /**
     * @override
     */
    _computeIsEmpty() {
        const isEmpty = this._super();
        const isRating = this.thread.lastMessage && this.thread.lastMessage.rating;
        return isRating || isEmpty;
    },
});
