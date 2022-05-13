/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
import { insertAndReplace } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/thread_view';

patchRecordMethods('ThreadView', {
    /**
     * @override
     */
    _computeMessageListView() {
        return this.threadViewer.qunitTest ? insertAndReplace() : this._super();
    },
});
