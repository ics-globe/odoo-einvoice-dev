/** @odoo-module **/

import ResPartnerFormController from 'web.ResPartnerFormController';

import FormRenderer from 'web.FormRenderer';
import FormView from 'web.FormView';
import viewRegistry from 'web.view_registry';

const ResPartnerFormView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Controller: ResPartnerFormController,
        Renderer: FormRenderer,
    }),
});

viewRegistry.add('res_partner_form_view', ResPartnerFormView);

export default ResPartnerFormView;
