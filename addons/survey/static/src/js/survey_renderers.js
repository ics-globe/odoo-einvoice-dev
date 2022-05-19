/** @odoo-module */

import KanbanRenderer from 'web.KanbanRenderer';
import ListRenderer from 'web.ListRenderer';

const SurveySampleMixin = {

    /**
     * Load and show the sample survey related to the clicked element,
     * when there is no survey to display.
     * We currently have 3 different samples to load:
     * - Sample Feedback Form
     * - Sample Certification
     * - Sample Live Presentation
     * 
     * @private
     * @param {Event} ev
     */
    _loadSample: function (ev) {
        this.do_action(this._rpc({
            model: 'survey.survey',
            method: $(ev.target).closest('.o_survey_sample_container').attr('action'),
        }));
    },
};

const SurveyKanbanRenderer = KanbanRenderer.extend(SurveySampleMixin, {
    events: _.extend({}, KanbanRenderer.prototype.events, {
        'click .o_survey_load_sample': '_loadSample',
    }),
});

const SurveyListRenderer = ListRenderer.extend(SurveySampleMixin, {
    events: _.extend({}, ListRenderer.prototype.events, {
        'click .o_survey_load_sample': '_loadSample',
    }),
});

export {
    SurveyKanbanRenderer,
    SurveyListRenderer,
};
