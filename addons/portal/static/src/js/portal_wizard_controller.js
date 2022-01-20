odoo.define('portal.portal_wizard_controller', function (require) {
    "use strict";

var FormController = require('web.FormController');

/**
 * @override
 * 
 * Override the default Controller to allow only one portal action to be performed at a time,
 * identified by selector 'o_portal_wizard_action_button'. As actions return a window opening
 * action with the same wizard id, we reactivate all buttons at the start.
 */
var PortalWizardFormController = FormController.extend({
    start: function () {
        this.$('.o_portal_wizard_action_button').prop('disabled', false);
        return this._super.apply(this, arguments);
    },
    _onButtonClicked: function (ev) {
        if (ev.data.attrs.class.split(' ').includes('o_portal_wizard_action_button')) {
            this.$('.o_portal_wizard_action_button').prop('disabled', true);
            this._callButtonAction(ev.data.attrs, ev.data.record).then(() => {
            // If an error happens, it will still enable buttons for the user.
            this.$('.o_portal_wizard_action_button').prop('disabled', false);
            });
        } else {
            this._super.apply(this, arguments);
        }
    },
});

return PortalWizardFormController;

});
