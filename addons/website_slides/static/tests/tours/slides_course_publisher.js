/** @odoo-module **/

import tour from 'web_tour.tour';
import slidesTourTools from '@website_slides/../tests/tours/slides_tour_tools';

/**
 * Global use case:
 * a user (website publisher) creates a course;
 * they update it;
 * they create some lessons in it;
 * they publishe it;
 */
tour.register('course_publisher', {
    // TODO: replace by wTourUtils.getClientActionURL when it's added
    url: '/web#action=website.website_editor&path=%2Fslides&website_id=1&cids=1',
    test: true
}, [{
    content: 'eLearning: click on New (top-menu)',
    trigger: 'div.o_new_content_container a'
}, {
    content: 'eLearning: click on New Course',
    trigger: 'a:contains("Course")'
}, {
    content: 'eLearning: set name',
    trigger: 'input[name="name"]',
    run: 'text How to Déboulonnate',
}, {
    content: 'eLearning: click on tags',
    trigger: '.o_field_many2manytags input',
    run: 'text Gard',
}, {
    content: 'eLearning: select gardener tag',
    trigger: '.ui-autocomplete a:contains("Gardener")',
    in_modal: false,
}, {
    content: 'eLearning: set description',
    trigger: '.oe_form_field_html[name="description"]',
    run: 'text Déboulonnate is very common at Fleurus',
}, {
    content: 'eLearning: we want reviews',
    trigger: '.o_field_boolean[name="allow_comment"] input',
}, {
    content: 'eLearning: seems cool, create it',
    trigger: 'button:contains("Save")',
}, {
    content: 'eLearning: launch course edition',
    trigger: '.o_edit_website_container a',
}, {
    content: 'eLearning: double click image to edit it',
    extra_trigger: 'iframe body.editor_enable',
    trigger: 'iframe img.o_wslides_course_pict',
    run: 'dblclick',
}, {
    content: 'eLearning: click "Add URL" to trigger URL box',
    trigger: '.o_upload_media_url_button',
}, {
    content: 'eLearning: add a bioutifoul URL',
    trigger: 'input.o_we_url_input',
    run: 'text https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/ThreeTimeAKCGoldWinnerPembrookeWelshCorgi.jpg/800px-ThreeTimeAKCGoldWinnerPembrookeWelshCorgi.jpg'
}, {
    content: 'eLearning: click "Add URL" really adding image',
    trigger: '.o_upload_media_url_button',
}, {
    content: 'eLearning: is the Corgi set ?',
    trigger: 'iframe img.o_wslides_course_pict',
    run: function () {
        const $imgCorgi = $('.o_website_editor iframe').contents().find('img.o_wslides_course_pict');
        if ($imgCorgi.attr('src').endsWith('GoldWinnerPembrookeWelshCorgi.jpg')) {
            $imgCorgi.addClass('o_wslides_tour_success');
        }
    },
}, {
    content: 'eLearning: the Corgi is set !',
    trigger: 'iframe img.o_wslides_course_pict.o_wslides_tour_success',
}, {
    content: 'eLearning: save course edition',
    trigger: 'button[data-action="save"]',
}, {
    content: 'eLearning: course create with current member',
    extra_trigger: 'iframe body:not(.editor_enable)',  // wait for editor to close
    trigger: 'iframe .o_wslides_js_course_join:contains("You\'re enrolled")',
    run: function () {} // check membership
}
].concat(
    slidesTourTools.addExistingCourseTag(true),
    slidesTourTools.addNewCourseTag('The Most Awesome Course', true),
    slidesTourTools.addSection('Introduction', true),
    slidesTourTools.addVideoToSection('Introduction', false, true),
    [{
    content: 'eLearning: publish newly added course',
    trigger: 'iframe span:contains("Dschinghis Khan - Dschinghis Khan (1979)")',  // wait for slide to appear
    // trigger: 'span.o_wslides_js_slide_toggle_is_preview:first',
    run: function () {
        $('.o_website_editor iframe').contents().find('span.o_wslides_js_slide_toggle_is_preview:first')[0].click();
    }
}]
//     [
// {
//     content: 'eLearning: move new course inside introduction',
//     trigger: 'div.o_wslides_slides_list_drag',
//     // run: 'drag_and_drop div.o_wslides_slides_list_drag ul.ui-sortable:first',
//     run: 'drag_and_drop div.o_wslides_slides_list_drag a.o_wslides_js_slide_section_add',
// }]
));
