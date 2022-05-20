/** @odoo-module **/

import { registry } from "@web/core/registry";
import { StateSelectionField } from "@web/fields/state_selection_field";

class ProjectStateSelectionField extends StateSelectionField {
    
    setup() {
        super.setup();
        this.excludedValues = ["to_define"];
        this.colorPrefix = "o_color_bubble_";
        // List of colors according to the selection value, see `project_update.py`
        this.colors = {
            on_track: 10,
            at_risk: 2,
            off_track: 1,
            on_hold: 4,
        };
    }
}

registry.category("fields").add('project_state_selection', ProjectStateSelectionField);
