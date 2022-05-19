/** @odoo-module **/

import core from 'web.core';
import fieldRegistry from 'web.field_registry';

import { PriorityWidget } from 'web.basic_fields';
import { sprintf } from "@web/core/utils/strings";

export const PrioritySwitchWidget = PriorityWidget.extend({

    on_attach_callback() {
        this._registerCommandSwitchPriority()
    },
    on_detach_callback(){
        this._unregisterCommandSwitchPriority()
    },

    _registerCommandSwitchPriority() {
        const self = this;
        if (self.viewType === "form") {
            const otherPriorityId = (parseInt(self.value) + 1) % self.field.selection.length;
            const otherPriority = self.field.selection[otherPriorityId];
            const getCommandDefinition = (env) => ({
                name: sprintf(env._t("Set priority as %s"), otherPriority[1]),
                options: {
                    activeElement: env.services.ui.getActiveElementOf(self.el),
                    category: "smart_action",
                    hotkey: "alt+r",
                },
                action() {
                    if (self.isDestroyed()) {
                        return
                    }
                    self._setValue(otherPriority[0].toString());
                },
            });
            core.bus.trigger("set_legacy_command", "web.PrioritySwitchWidget.switchPriority", getCommandDefinition);
        }
    },

    _unregisterCommandSwitchPriority() {
        core.bus.trigger("remove_legacy_command", "web.PrioritySwitchWidget.switchPriority");
    },
});

fieldRegistry.add('priority_switch', PrioritySwitchWidget);
