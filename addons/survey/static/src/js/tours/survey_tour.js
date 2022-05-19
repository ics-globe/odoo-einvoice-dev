/** @odoo-module */

import { _t } from 'web.core';
import { Markup } from 'web.utils';
import tour from 'web_tour.tour';

tour.register('survey_tour', {
    url: '/web',
    rainbowManMessage: _t('Congratulations! You are now ready to gather data real fast :-)'),
}, [
    ...tour.stepUtils.goToAppSteps('survey.menu_surveys', Markup('Ready to change the way you <b>ask questions</b>?')),
{
    trigger: 'body:has(.o_survey_load_sample) .o_survey_sample_container',
    content: Markup(_t('Load a <b>template</b> to get started quickly.')),
    position: 'bottom',
}, {
    trigger: 'button[name=action_test_survey]',
    content: Markup(_t('Let\'s give it a spin!')),
    position: 'bottom',
}, {
    trigger: 'button[type=submit]',
    content: Markup(_t('Let\'s get started')),
    position: 'bottom',
}, {
    trigger: 'button[type=submit]',
    content: Markup(_t('Whenever you pick an answer, Odoo <b>saves</b> the result for you.')),
    position: 'bottom', 
}, {
    trigger: 'button[type=submit]',
    content: Markup(_t('Only a single question left!')),
    position: 'bottom',
}, {
    trigger: 'button[type=submit]',
    content: Markup(_t('Now that you are done, submit your form.')),
    position: 'bottom',
}, {
    trigger: '.o_survey_review a',
    content: Markup(_t('Let\'s have a look at your results!')),
    position: 'bottom',
}, {
    trigger: '.alert-info a',
    content: Markup(_t('Now, use this <b>shortcut</b> to go back to Survey.')),
    position: 'bottom',
}, {
    trigger: 'button[name=action_survey_user_input_completed]',
    content: Markup(_t('Here, you can <b>overview all the results</b>.')),
    position: 'bottom',
}, {
    trigger: 'td[name=survey_id]',
    content: Markup(_t('Let\'s open your own Survey.')),
    position: 'bottom',
}, {
    trigger: '.breadcrumb a:contains("Feedback Form")',
    content: Markup(_t('Use the <b>breadcrumbs</b> to quickly go back to the Survey.')),
    position: 'bottom',
}
]);
