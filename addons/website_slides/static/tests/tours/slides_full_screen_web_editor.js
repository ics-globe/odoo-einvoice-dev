/** @odoo-module **/

import tour from 'web_tour.tour';

/**
 * Global use case:
 * - a user (website publisher) lands on the fullscreen view of a course ;
 * - they click on the website editor "Edit" button ;
 * - they are redirected to the non-fullscreen view with the editor opened.
 *
 * This tour tests a fix made when editing a course in fullscreen view.
 * See "Fullscreen#_onWebEditorClick" for more information.
 *
 */
tour.register('full_screen_web_editor', {
    url: '/slides',
    test: true
}, [{
    // open to the course
    trigger: 'a:contains("Basics of Gardening")'
}, {
    // click on a slide to open the fullscreen view
    trigger: 'a.o_wslides_js_slides_list_slide_link:contains("Home Gardening")'
}, {
    trigger: '.o_wslides_fs_main',
    run: function () {} // check we land on the fullscreen view
}, {
    trigger: '.o_frontend_to_backend_edit_btn',
}, {
// TODO: uncomment this when edit button behaviour changes.
//     // click on the main "Edit" button to open the web editor
//     trigger: '.o_edit_website_container a',
// }, {
    trigger: 'iframe .o_wslides_lesson_main',
    run: function () {} // check we are redirected on the detailed view
}, {
    trigger: 'body.editor_has_snippets',
    run: function () {} // check the editor is automatically opened on the detailed view
}]);
