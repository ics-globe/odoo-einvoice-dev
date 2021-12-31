/** @odoo-module **/

import { WebClient } from '@web/webclient/webclient';
import { patch } from 'web.utils';
import { registry } from "@web/core/registry";

patch(WebClient.prototype, 'website_web_client', {
    setup() {
        this._super();

        if (this.env.debug) {
            registry.category('website_systray').add('DebugMenu', registry.category('systray').get('web.debug_mode_menu'), { sequence: 100 });
        }
    },
});
