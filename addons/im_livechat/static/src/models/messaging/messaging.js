/** @odoo-module **/

import { addFields } from '@mail/model/model_core';
import { one2many } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging/messaging';

addFields('mail.messaging', {
    /**
     * All livechats that are known.
     */
    livechats: one2many('mail.thread', {
        inverse: 'messagingAsLivechat',
        readonly: true,
    }),
});
