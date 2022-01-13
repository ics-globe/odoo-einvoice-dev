/** @odoo-module **/

import { click, editInput } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            trim: true,
                        },
                        empty_string: {
                            string: "Empty string",
                            type: "char",
                            default: false,
                            searchable: true,
                            trim: true,
                        },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                    },
                    records: [
                        {
                            foo: "yop",
                        },
                        {
                            foo: "blip",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("EmailField");

    QUnit.test("EmailField in form view", async function (assert) {
        assert.expect(7);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="foo" widget="email"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            resId: 1,
        });
        let mailtoLink = form.el.querySelector("a.o_field_email.o_form_uri.o_text_overflow");
        assert.containsOnce(form, mailtoLink, "should have a anchor with correct classes");
        assert.strictEqual(mailtoLink.innerText, "yop", "the value should be displayed properly");
        assert.hasAttrValue(mailtoLink, "href", "mailto:yop", "should have proper mailto prefix");

        // switch to edit mode and check the result
        await click(form.el.querySelector(".o_form_button_edit"));
        const mailtoEdit = form.el.querySelector('input[type="email"].o_field_email');
        assert.containsOnce(form, mailtoEdit, "should have an input for the email field");
        assert.strictEqual(
            mailtoEdit.value,
            "yop",
            "input should contain field value in edit mode"
        );

        // change value in edit mode
        await editInput(form.el, "input[type='email'].o_field_email", "new");

        // save
        await click(form.el.querySelector(".o_form_button_save"));
        mailtoLink = form.el.querySelector("a.o_field_email");
        assert.strictEqual(mailtoLink.innerText, "new", "new value should be displayed properly");
        assert.hasAttrValue(
            mailtoLink,
            "href",
            "mailto:new",
            "should still have proper mailto prefix"
        );
    });

    QUnit.test("EmailField in editable list view", async function (assert) {
        assert.expect(10);

        const list = await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree edit="1" editable="bottom"><field name="foo"  widget="email"/></tree>',
        });
        assert.strictEqual(
            list.el.querySelectorAll("tbody td:not(.o_list_record_selector) a").length,
            2,
            "should have 2 cells with a link"
        );
        assert.strictEqual(
            list.el.querySelector("tbody td:not(.o_list_record_selector)").innerText,
            "yop",
            "value should be displayed properly as text"
        );

        let mailtoLink = list.el.querySelectorAll("a.o_field_email");
        assert.containsN(
            list,
            ".o_field_email.o_field_widget[name='foo'] a",
            2,
            "should have 2 anchors with correct classes"
        );
        assert.hasAttrValue(
            mailtoLink[0],
            "href",
            "mailto:yop",
            "should have proper mailto prefix"
        );
        // Edit a line and check the result
        let cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        await click(cell);
        assert.hasClass(cell.parentElement, "o_selected_row", "should be set as edit mode");
        const mailField = cell.querySelector("input");
        assert.strictEqual(
            mailField.value,
            "yop",
            "should have the correct value in internal input"
        );
        await editInput(cell, "input", "new");

        // save
        await click(list.el.querySelector(".o_list_button_save"));
        cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        assert.doesNotHaveClass(
            cell.parentElement,
            "o_selected_row",
            "should not be in edit mode anymore"
        );
        assert.strictEqual(
            list.el.querySelector("tbody td:not(.o_list_record_selector)").innerText,
            "new",
            "value should be properly updated"
        );
        mailtoLink = list.el.querySelectorAll(".o_field_widget[name='foo'] a");
        assert.strictEqual(mailtoLink.length, 2, "should still have anchors with correct classes");
        assert.hasAttrValue(
            mailtoLink[0],
            "href",
            "mailto:new",
            "should still have proper mailto prefix"
        );
    });

    QUnit.test("EmailField with empty value", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                "<form>" +
                "<sheet>" +
                "<group>" +
                '<field name="empty_string" widget="email"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
        });

        await click(form.el.querySelector(".o_form_button_save"));
        const mailtoLink = form.el.querySelector("a.o_field_email");
        assert.strictEqual(mailtoLink.innerText, "", "the value should be displayed properly");
    });

    QUnit.test("EmailField trim user value", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: '<form><field name="foo" widget="email"/></form>',
        });
        await editInput(form.el, ".o_field_widget[name='foo'] input", "  abc@abc.com  ");
        const mailFieldInput = form.el.querySelector('.o_field_widget[name="foo"] input');
        await click(form.el.querySelector(".o_form_button_save"));
        await click(form.el.querySelector(".o_form_button_edit"));
        assert.strictEqual(
            mailFieldInput.value,
            "abc@abc.com",
            "Foo value should have been trimmed"
        );
    });

    QUnit.test(
        "readonly EmailField is properly rerendered after been changed by onchange",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.records[0].foo = "dolores.abernathy@delos";
            const form = await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch:
                    '<form string="Partners">' +
                    "<sheet>" +
                    "<group>" +
                    '<field name="int_field" on_change="1"/>' + // onchange to update mobile in readonly mode directly
                    '<field name="foo" widget="email" readonly="1"/>' + // readonly only, we don't want to go through write mode
                    "</group>" +
                    "</sheet>" +
                    "</form>",
                resId: 1,
                mockRPC(route, { method }) {
                    if (method === "onchange") {
                        return Promise.resolve({
                            value: {
                                foo: "lara.espin@unknown", // onchange to update foo in readonly mode directly
                            },
                        });
                    }
                },
            });
            // check initial rendering
            assert.strictEqual(
                form.el.querySelector(".o_field_email").innerText,
                "dolores.abernathy@delos",
                "Initial email text should be set"
            );

            // edit the phone field, but with the mail in readonly mode
            await click(form.el.querySelector(".o_form_button_edit"));
            await editInput(form.el, ".o_field_widget[name='int_field'] input", 3);
            await click(form.el.querySelector(".o_form_button_save"));

            // check rendering after changes
            assert.strictEqual(
                form.el.querySelector(".o_field_email").innerText,
                "lara.espin@unknown",
                "email text should be updated"
            );
        }
    );
});
