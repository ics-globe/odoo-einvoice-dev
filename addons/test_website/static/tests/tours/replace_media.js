/** @odoo-module **/

import tour from 'web_tour.tour';

/**
 * The purpose of this tour is to check the media replacement flow:
 *
 * -> go to edit mode
 * -> drag a Picture snippet into page content
 * -> select image
 * -> check image size is displayed
 * -> click on replace image
 * -> select gif
 * -> check image size is NOT displayed
 */

tour.register('test_replace_media', {
    url: '/',
    test: true
}, [
    {
        content: "enter edit mode",
        trigger: "a[data-action=edit]"
    },
    {
        content: "drop picture snippet",
        trigger: "#oe_snippets .oe_snippet[name='Picture'] .oe_snippet_thumbnail:not(.o_we_already_dragging)",
        extra_trigger: "body.editor_enable.editor_has_snippets",
        moveTrigger: ".oe_drop_zone",
        run: "drag_and_drop #wrap",
    },
    {
        content: "select image",
        trigger: "#wrapwrap .s_picture figure img",
    },
    {
        content: "ensure image size is displayed",
        trigger: "#oe_snippets we-title:contains('Image') span.o_we_image_weight:contains('kb')",
        run: function () {}, // check
    },
    {
        content: "replace image",
        trigger: "#oe_snippets we-button[data-replace-media]",
    },
    {
        content: "select gif",
        trigger: ".o_select_media_dialog img[title='sample.gif']",
    },
    {
        content: "ensure image size is not displayed",
        trigger: "#oe_snippets we-title:contains('Image'):not(:has(span.o_we_image_weight:not(.d-none)))",
        run: function () {}, // check
    },
]);
