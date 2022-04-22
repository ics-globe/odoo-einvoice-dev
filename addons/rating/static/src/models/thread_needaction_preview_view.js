/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure the model definition is loaded before the patch
import '@mail/models/thread_needaction_preview_view';

patchRecordMethods('ThreadNeedactionPreviewView', {
    /**
     * @override
     */
    _computeIsEmpty() {
        const isEmpty = this._super();
        const isRating = this.thread.lastNeedactionMessageAsOriginThread && this.thread.lastNeedactionMessageAsOriginThread.rating;
        return isRating || isEmpty;
    },
});
