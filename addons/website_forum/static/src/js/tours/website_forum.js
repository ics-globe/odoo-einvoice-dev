odoo.define("website_forum.tour_forum", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");
    const wTourUtils = require('website.tour_utils');

    var _t = core._t;

    tour.register("question", {
        url: wTourUtils.getClientActionUrl('/forum/1'),
    }, [{
        trigger: "iframe .o_forum_ask_btn",
        position: "left",
        content: _t("Create a new post in this forum by clicking on the button."),
    }, {
        trigger: "iframe input[name=post_name]",
        position: "top",
        content: _t("Give your post title."),
    }, {
        trigger: "iframe .note-editable p",
        extra_trigger: "iframe input[name=post_name]:not(:propValue(\"\"))",
        content: _t("Put your question here."),
        position: "bottom",
        run: "text",
    }, {
        trigger: "iframe .select2-choices",
        extra_trigger: "iframe .note-editable p:not(:containsExact(\"<br>\"))",
        content: _t("Insert tags related to your question."),
        position: "top",
        run: function (actions) {
            actions.auto("iframe input[id=s2id_autogen2]");
        },
    }, {
        trigger: "iframe button:contains(\"Post\")",
        extra_trigger: "iframe input[id=s2id_autogen2]:not(:propValue(\"Tags\"))",
        content: _t("Click to post your question."),
        position: "bottom",
    }, {
        extra_trigger: 'iframe div.modal.modal_shown',
        trigger: "iframe .modal-header button.close",
        auto: true,
    },
    {
        trigger: "iframe a:contains(\"Answer\").collapsed",
        content: _t("Click to answer."),
        position: "bottom",
    },
    {
        trigger: "iframe .note-editable p",
        content: _t("Put your answer here."),
        position: "bottom",
        run: "text",
    }, {
        trigger: "iframe button:contains(\"Post Answer\")",
        extra_trigger: "iframe .note-editable p:not(:containsExact(\"<br>\"))",
        content: _t("Click to post your answer."),
        position: "bottom",
    }, {
        extra_trigger: 'iframe div.modal.modal_shown',
        trigger: "iframe .modal-header button.close",
        auto: true,
    }, {
        trigger: "iframe .o_wforum_validate_toggler[data-karma]:first",
        content: _t("Click here to accept this answer."),
        position: "right",
    }]);
});
