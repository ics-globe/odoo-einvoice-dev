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
 * -> click on replace image
 * -> select pictogram tab
 * -> select an icon
 * -> check icon options are displayed
 * -> select footer
 * -> select icon
 * -> check icon options are still displayed
 * -> click on replace icon
 * -> select video tab
 * -> enter a video URL
 * -> wait for preview
 * -> confirm selection
 * -> wait for dialog to disappear
 * -> check video options are displayed
 * -> click on replace video
 * -> select pictogram tab
 * -> select an icon
 * -> check icon options are displayed
 * -> select footer
 * -> select icon
 * -> check icon options are still displayed
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
    {
        content: "replace image",
        trigger: "#oe_snippets we-button[data-replace-media]",
    },
    {
        content: "go to pictogram tab",
        trigger: ".o_select_media_dialog .nav-link#editor-media-icon-tab",
    },
    {
        content: "select an icon",
        trigger: ".o_select_media_dialog .tab-pane#editor-media-icon span.fa-lemon-o",
    },
    {
        content: "ensure icon block is displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
        run: function () {}, // check
    },
    {
        content: "select footer",
        trigger: "#wrapwrap footer",
    },
    {
        content: "select icon",
        trigger: "#wrapwrap .s_picture figure span.fa-lemon-o",
    },
    {
        content: "ensure icon block is still displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
        run: function () {}, // check
    },
    {
        content: "replace icon",
        trigger: "#oe_snippets we-button[data-replace-media]",
    },
    {
        content: "go to video tab",
        trigger: ".o_select_media_dialog .nav-link#editor-media-video-tab",
    },
    {
        content: "enter a video URL",
        trigger: ".o_select_media_dialog #o_video_text",
        // Design your first web page.
        run: "text https://www.youtube.com/watch?v=Dpq87YCHmJc",
    },
    {
        content: "wait for preview to appear",
        trigger: ".o_select_media_dialog div.media_iframe_video iframe",
        run: function () {}, // check
    },
    {
        content: "confirm selection",
        trigger: ".o_select_media_dialog .modal-footer .btn-primary",
    },
    {
        content: "wait for dialog to be closed",
        trigger: ".o_dialog_container:not(:has(div))",
        run: function () {}, // check
    },
    {
        content: "ensure video option block is displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Video')",
        run: function () {}, // check
    },
    {
        content: "replace image",
        trigger: "#oe_snippets we-button[data-replace-media]",
    },
    {
        content: "go to pictogram tab",
        trigger: ".o_select_media_dialog .nav-link#editor-media-icon-tab",
    },
    {
        content: "select an icon",
        trigger: ".o_select_media_dialog .tab-pane#editor-media-icon span.fa-lemon-o",
    },
    {
        content: "ensure icon block is displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
        run: function () {}, // check
    },
    {
        content: "select footer",
        trigger: "#wrapwrap footer",
    },
    {
        content: "select icon",
        trigger: "#wrapwrap .s_picture figure span.fa-lemon-o",
    },
    {
        content: "ensure icon block is still displayed",
        trigger: "#oe_snippets we-customizeblock-options we-title:contains('Icon')",
        run: function () {}, // check
    },
]);
