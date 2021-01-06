odoo.define('product.tour_product_wizard_merge', function (require) {
    'use strict';

    var tour = require('web_tour.tour');

    // This tour relies on demo data and python test.
    tour.register('product_wizard_merge_test_01', {
        test: true,
        url: '/web?debug=1#action=product.product_template_action',
    },
    [
        {
            content: "open product template list view",
            trigger: '.o_cp_switch_buttons button.o_list',
        },
        {
            content: "select Corner Desk Left Sit",
            trigger: '.o_list_view tr.o_data_row:contains("Corner Desk Left Sit") input[type="checkbox"]',
        },
        {
            content: "select Corner Desk Right Sit",
            trigger: '.o_list_view tr.o_data_row:contains("Corner Desk Right Sit") input[type="checkbox"]',
        },
        {
            content: "open action top menu",
            trigger: '.o_cp_action_menus ul.show a:contains("Merge products")',
        },
        {
            content: "click on merge action",
            trigger: '.o_product_wizard_merge button[name="action_merge"]',
        },
        {
            content: "Merge is finished (redirection to form view)",
            trigger: '.o_form_view .o_field_widget[name="name"]:contains("Corner Desk Left Sit")',
        },
        {
            content: "Check if the merge is finished (redirection to form view)",
            trigger: '.o_form_view',
            run: function () {},
        },
    ]);
});
