/** @odoo-module  */

import { patch } from 'web.utils';
import { NavBar } from '@web/webclient/navbar/navbar';

const { onWillStart } = owl;

patch(NavBar.prototype, 'website_links_navbar', {
    setup() {
        this._super();

        onWillStart(() => {
            this.websiteEditingMenus['website_links.menu_link_tracker'] = {
                openWidget: () => this.websiteService.goToWebsite({ path: `/r?u=${this.websiteService.contentWindow.location.href}` }),
                isDisplayed: () => true,
                options: () => {},
            };
        }, () => []);
    },
});
