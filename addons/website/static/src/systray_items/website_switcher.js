/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component } = owl;

class WebsiteSwitcherSystray extends Component {
    setup() {
        this.websiteService = useService('website');
    }

    getElements() {
        return this.websiteService.websites.map((website) => ({
            name: website.name,
            callback: () => {
                if (website.domain && website.domain !== window.location.origin) {
                    const { location: { pathname, search, hash } } = this.websiteService.contentWindow;
                    const path = pathname + search + hash;
                    window.location.href = `${website.domain}/web#action=website.website_editor&path=${encodeURI(path)}&website_id=${website.id}`;
                } else {
                    this.websiteService.goToWebsite({ websiteId: website.id });
                }
            },
        }));
    }
}
WebsiteSwitcherSystray.template = "website.WebsiteSwitcherSystray";
WebsiteSwitcherSystray.components = {
    Dropdown,
    DropdownItem,
};

export const systrayItem = {
    Component: WebsiteSwitcherSystray,
};

registry.category("website_systray").add("WebsiteSwitcher", systrayItem, { sequence: 11 });
