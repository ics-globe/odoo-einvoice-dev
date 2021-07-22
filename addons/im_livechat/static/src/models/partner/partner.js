/** @odoo-module **/

import { registerClassPatchModel } from '@discuss/model/model_core';

let nextPublicId = -1;

registerClassPatchModel('res.partner', 'im_livechat/static/src/models/partner/partner.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    getNextPublicId() {
        const id = nextPublicId;
        nextPublicId -= 1;
        return id;
    },
});

