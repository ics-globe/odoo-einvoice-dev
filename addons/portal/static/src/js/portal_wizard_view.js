odoo.define('portal.portal_wizard_view', function (require) {
    "use strict";

const PortalWizardController = require('portal.portal_wizard_controller');
const FormView = require('web.FormView');
const viewRegistry = require('web.view_registry');

var PortalWizardUserFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: PortalWizardController,
    }),
});

viewRegistry.add('portal_wizard_user_form', PortalWizardUserFormView);

return PortalWizardUserFormView;

});
