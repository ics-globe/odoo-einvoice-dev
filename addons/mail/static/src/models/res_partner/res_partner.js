  /** @odoo-module **/

import { registerFieldPatchModel } from '@discuss/model/model_core';
import { one2many } from '@discuss/model/model_field';

registerFieldPatchModel('res.partner', 'mail', {
    mailMessagesAsAuthor: one2many('mail.message', {
        inverse: 'author',
    }),
});
