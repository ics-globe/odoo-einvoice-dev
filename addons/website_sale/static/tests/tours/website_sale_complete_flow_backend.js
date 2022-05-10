/** @odoo-module **/

import tour from 'web_tour.tour';
import wTourUtils from 'website.tour_utils';

tour.register('website_sale_tour_backend', {
    test: true,
    url: wTourUtils.getClientActionUrl('/shop/cart', true),
},
    [
        {
            content: "open customize tab",
            extra_trigger: '#oe_snippets.o_loaded',
            trigger: '.o_we_customize_snippet_btn',
        },
        {
            content: "Enable Extra step",
            extra_trigger: '#oe_snippets .o_we_customize_panel',
            trigger: '[data-customize-website-views="website_sale.extra_info_option"] we-checkbox',
        },
        {
            content: "check that the iframe is reloading",
            trigger: '.o_loading_dummy',
            run: () => {}, // It's a check.
        },
        {
            content: "click on save button after the reload",
            trigger: 'div:not(.o_loading_dummy) > #oe_snippets button[data-action="save"]',
            run: 'click',
        },
        {
            content: "wait to exit edit mode",
            trigger: '.o_website_editor:not(.editor_has_snippets)',
        },
    ],
);
