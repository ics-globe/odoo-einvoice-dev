/** @odoo-module **/

import core from 'web.core';
import fieldRegistry from 'web.field_registry';

import { StateSelectionWidget } from 'web.basic_fields';
import { sprintf } from "@web/core/utils/strings";

export const KanbanStateSwitchWidget = StateSelectionWidget.extend({

    on_attach_callback() {
        this._registerCommandSwitchKanbanState()
    },
    on_detach_callback(){
        this._unregisterCommandSwitchKanbanState()
    },

    _registerCommandSwitchKanbanState() {
        const self = this;
        if (self.viewType === "form") {
            for (let indexAndState of self.field.selection.entries()) {
                const index = indexAndState[0];
                const hotkey = String.fromCharCode(106 + index); // 'j', 'k', 'l'
                const value = indexAndState[1][0];
                const label = indexAndState[1][1];
                if (value === this.value) continue;

                let getCommandDefinition = (env) => ({
                        name: sprintf(env._t("Set kanban state as %s"), label),
                        options: {
                            activeElement: env.services.ui.getActiveElementOf(self.el),
                            category: "smart_action",
                            hotkey: "alt+" + hotkey,
                        },
                        action() {
                            self._setValue(value);
                        },
                });

                core.bus.trigger("set_legacy_command", "web.FieldStatus.moveToState" + value, getCommandDefinition);
            }
        }
    },

    _unregisterCommandSwitchKanbanState() {
        for (let state of this.field.selection) {
            const value = state[0];
            if (value === this.value) continue;
            core.bus.trigger("remove_legacy_command", "web.FieldStatus.moveToState" + value);
        }
    },
})

fieldRegistry.add('kanban_state_switch', KanbanStateSwitchWidget);
