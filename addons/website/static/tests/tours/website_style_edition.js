odoo.define("website.tour.website_style_edition", function (require) {
"use strict";

const tour = require("web_tour.tour");

const TARGET_FONT_SIZE = 30;

tour.register("website_style_edition", {
    test: true,
    url: "/",
}, [{
    content: "Enter edit mode",
    trigger: 'a.o_frontend_to_backend_edit_btn',
}, {
    content: "Go to theme options",
    extra_trigger: '#oe_snippets.o_loaded',
    trigger: '.o_we_customize_theme_btn',
}, {
    content: "Change font size",
    trigger: '[data-variable="font-size-base"] input',
    run: `text_blur ${TARGET_FONT_SIZE}`,
}, {
    content: "Save",
    trigger: '[data-action="save"]',
}, {
    content: "Check the font size was properly adapted",
    trigger: 'iframe body:not(.editor_enable) #wrapwrap',
    run: function (actions) {
        const style = window.getComputedStyle(this.$anchor[0]);
        if (style.fontSize !== `${TARGET_FONT_SIZE}px`) {
            console.error(`Expected the font-size to be equal to ${TARGET_FONT_SIZE}px but found ${style.fontSize} instead`);
        }
    },
}]);
});
