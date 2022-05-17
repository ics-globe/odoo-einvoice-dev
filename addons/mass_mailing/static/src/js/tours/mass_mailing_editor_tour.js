odoo.define('mass_mailing.mass_mailing_editor_tour', function (require) {
    "use strict";

    var tour = require('web_tour.tour');

    tour.register('mass_mailing_editor_tour', {
        url: '/web',
        test: true,
    }, [tour.stepUtils.showAppsMenuItem(), {
        trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
    }, {
        trigger: 'button.o_list_button_add',
    }, {
        trigger: 'div[name="contact_list_ids"] .o_input_dropdown > input[type="text"]',
    }, {
        trigger: 'li.ui-menu-item',
    }, {
        trigger: '[name="body_arch"] iframe #empty',
    }, {
        trigger: '[name="body_arch"] iframe .o_editable'
    }, {
        trigger: '[name="body_arch"] iframe #email_designer_default_body [name="Title"] .ui-draggable-handle',
        run: function (actions) {
            actions.drag_and_drop('[name="body_arch"] iframe .o_editable', this.$anchor);
        }
    }, {
        trigger: '[name="body_arch"] iframe .o_editable h1'
    }, {
        trigger: 'button.o_form_button_save',
    }, {
        trigger: 'label.o_field_invalid',
    }, {
        trigger: '[name="body_arch"] iframe .o_editable h1'
    }, {
        trigger: '[name="body_arch"] iframe .odoo-editor-editable',
        run: function () {
            const ownerDocument = this.$anchor[0].ownerDocument;
            const paragraph = ownerDocument.createElement('p');
            const linebreak = ownerDocument.createElement('br');
            paragraph.append(linebreak);
            const fragment = new DocumentFragment();
            fragment.append(paragraph);
            this.$anchor[0].replaceChildren(...fragment.childNodes);
        }
    }, {
        trigger: 'input[name="subject"]',
        run: 'text Test',
    }, {
        trigger: 'button.o_form_button_save',
    }, {
        trigger: 'iframe.o_readonly',
    }]);
});
