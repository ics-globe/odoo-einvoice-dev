odoo.define('survey.SurveyFormView', function (require) {
'use strict';

var SurveyFormController = require('survey.SurveyFormController');
var FormRenderer = require('web.FormRenderer');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');

var SurveyFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: SurveyFormController,
        Renderer: FormRenderer,
    }),
});

viewRegistry.add('survey_survey_form', SurveyFormView);

return SurveyFormView;

});
