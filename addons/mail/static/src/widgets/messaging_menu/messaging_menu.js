odoo.define('mail/static/src/widgets/messaging_menu/messaging_menu.js', function (require) {
'use strict';

const components = {
    MessagingMenu: require('mail/static/src/components/messaging_menu/messaging_menu.js'),
};

const SystrayMenu = require('web.SystrayMenu');
const Widget = require('web.Widget');

const { ComponentWrapper, WidgetAdapterMixin } = require('web.OwlCompatibility');

/**
 * Odoo Widget, necessary to instantiate component.
 */
const MessagingMenu = Widget.extend(WidgetAdapterMixin, {
    template: 'mail.widgets.MessagingMenu',
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.component = new ComponentWrapper(this, components.MessagingMenu, null);
        return this.component.mount(this.el);
    },

    on_attach_callback() {
        this.el.parentNode.insertBefore(this.component.el, this.el)
        this.el.parentNode.removeChild(this.el)
        WidgetAdapterMixin.on_attach_callback.apply(this, arguments)
    },
});

// Systray menu items display order matches order in the list
// lower index comes first, and display is from right to left.
// For messagin menu, it should come before activity menu, if any
// otherwise, it is the next systray item.
const activityMenuIndex = SystrayMenu.Items.findIndex(SystrayMenuItem =>
    SystrayMenuItem.prototype.name === 'activity_menu');
if (activityMenuIndex > 0) {
    SystrayMenu.Items.splice(activityMenuIndex, 0, MessagingMenu);
} else {
    SystrayMenu.Items.push(MessagingMenu);
}

return MessagingMenu;

});
