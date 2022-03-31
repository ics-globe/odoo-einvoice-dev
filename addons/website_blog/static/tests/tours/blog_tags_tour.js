/** @odoo-module **/

import tour from 'web_tour.tour';

/**
 * Makes sure that blog tags can be created and removed.
 */
tour.register('blog_tags', {
    test: true,
    url: '/blog',
}, [{
        trigger: "article[name=blog_post] a",
        content: "Go to first blog.",
    }, {
        trigger: "section#o_wblog_post_main",
        content: "Wait for single blog post.",
        run: () => {}, // it's a check
    }, {
        trigger: "a[data-action=edit]",
        content: "Edit blog post.",
    }, {
        trigger: "we-customizeblock-option:contains(Tags) we-toggler",
        content: "Open tag dropdown.",
    }, {
        trigger: "we-customizeblock-option:contains(Tags) we-selection-items .o_we_m2o_create input",
        content: "Enter tag name.",
        run: "text testtag",
    }, {
        trigger: "we-customizeblock-option:contains(Tags) we-selection-items .o_we_m2o_create we-button",
        content: "Click Create.",
    }, {
        trigger: "we-customizeblock-option:contains(Tags) we-list input[data-name=testtag]",
        content: "Verify tag appears in options.",
        run: () => {}, // it's a check
    }, {
        trigger: "button[data-action=save]",
        content: "Click Save.",
    }, {
        trigger: "#o_wblog_post_content .badge:contains(testtag)",
        content: "Verify tag appears in blog post.",
        run: () => {}, // it's a check
    }, {
        trigger: "a[data-action=edit]",
        content: "Edit blog post.",
    }, {
        trigger: "we-customizeblock-option:contains(Tags) we-list tr:has(input[data-name=testtag]) we-button.fa-minus",
        content: "Remove tag.",
    }, {
        trigger: "we-customizeblock-option:contains(Tags) we-list:not(:has(input[data-name=testtag]))",
        content: "Verify tag does not appear in options anymore.",
        run: () => {}, // it's a check
    }, {
        trigger: "button[data-action=save]",
        content: "Click Save.",
    }, {
        trigger: "#o_wblog_post_content div:has(.badge):not(:contains(testtag))",
        content: "Verify tag does not appear in blog post anymore.",
        run: () => {}, // it's a check
    }]
);
