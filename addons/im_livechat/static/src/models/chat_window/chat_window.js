/** @odoo-module **/

import { registerInstancePatchModel } from '@discuss/model/model_core';

registerInstancePatchModel('discuss.chat_window', 'im_livechat/static/src/models/chat_window/chat_window.js', {

    /**
     * @override
     */
    close({ notifyServer } = {}) {
        if (
            this.thread &&
            this.thread.model === 'mail.channel' &&
            this.thread.channel_type === 'livechat' &&
            this.thread.mainCache.isLoaded &&
            this.thread.messages.length === 0
        ) {
            notifyServer = true;
            this.thread.unpin();
        }
        this._super({ notifyServer });
    }
});
