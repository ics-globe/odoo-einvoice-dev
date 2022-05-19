/** @odoo-module **/

import core from 'web.core';
import fieldRegistry from 'web.field_registry';

import { FieldStatus } from 'web.relational_fields';
import { sprintf } from "@web/core/utils/strings";

export const StateSwitchWidget = FieldStatus.extend({

    on_attach_callback() {
        this._super.apply(this, arguments);
        this._registerCommandSwitchState()
    },
    on_detach_callback(){
        this._super.apply(this, arguments);
        this._unregisterCommandSwitchState()
    },

    _registerCommandSwitchState() {
        const self = this;
        if (self.viewType === "form") {
            const nextStateIndex = self.status_information.findIndex(state => state.selected) + 1;
            if (nextStateIndex >= self.status_information.length) return;

            let getCommandDefinition = (env) => ({
                    name: sprintf(env._t("Move to next %s"), self.string),
                    options: {
                        activeElement: env.services.ui.getActiveElementOf(self.el),
                        category: "smart_action",
                        hotkey: "alt+x",
                    },
                    action() {
                        self._setValue(nextStateIndex);
                    },
            });

            core.bus.trigger("set_legacy_command", "web.FieldStatus.moveToNextState", getCommandDefinition);
        }
    },

    _unregisterCommandSwitchState() {
        core.bus.trigger("remove_legacy_command", "web.FieldStatus.moveToNextState");
    },
})

fieldRegistry.add('state_switch', StateSwitchWidget);
