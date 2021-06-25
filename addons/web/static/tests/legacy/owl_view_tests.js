/** @odoo-module */

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { fakeTitleService } from "@web/../tests/helpers/mock_services";
import { getFixture, makeDeferred, mount, nextTick } from "@web/../tests/helpers/utils";
import { addLegacyMockEnvironment } from "@web/../tests/webclient/helpers";
import { createDebugContext } from "@web/core/debug/debug_context";
import { dialogService } from "@web/core/dialog/dialog_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { View } from "@web/legacy/owl_view";
import { viewService } from "@web/views/view_service";
import { actionService } from "@web/webclient/actions/action_service";
import { ComponentWrapper } from "web.OwlCompatibility";
import Widget from "web.Widget";

const { Component, reactive, useState, xml } = owl;
const serviceRegistry = registry.category("services");

let target;
let serverData;

const prepareEnv = async (mockRPC) => {
    const baseEnv = await makeTestEnv({ serverData, mockRPC });
    const env = { ...baseEnv, ...createDebugContext(baseEnv) };

    addLegacyMockEnvironment(env, { withLegacyMockServer: true, models: serverData.models });

    odoo.__WOWL_DEBUG__ = {
        root: { env },
    };

    return env;
};

QUnit.module("Owl view", ({ beforeEach }) => {
    beforeEach(async () => {
        serviceRegistry
            .add("action", actionService)
            .add("notification", notificationService)
            .add("view", viewService)
            .add("title", fakeTitleService)
            .add("dialog", dialogService)
            .add("orm", ormService);

        target = getFixture();
        serverData = {
            models: {
                "hobbit": {
                    fields: {
                        foo: { type: "char", string: "Foo", searchable: true },
                    },
                    records: [
                        { id: 1, foo: "frodo" },
                        { id: 2, foo: "sam" },
                        { id: 3, foo: "merry" },
                        { id: 4, foo: "pippin" },
                    ],
                },
            },
            views: {
                "hobbit,false,list": /* xml */`
                    <list>
                        <field name="foo" />
                    </list>
                `,
                "hobbit,false,form": /* xml */`
                    <form>
                        <field name="foo" />
                    </form>
                `,
                "hobbit,false,search": /* xml */`
                    <search>
                        <field name="foo" />
                    </search>
                `,
            },
        }
    });

    QUnit.test("Instantiate multiple view components", async (assert) => {
        assert.expect(8);

        let parentState = reactive({
            resModel: "hobbit",
            resId: 1,
            domain: [],
        });
        class Parent extends Component {
            setup() {
                this.state = useState(parentState);
            }
        }

        Parent.components = { View };
        Parent.template = xml/* xml */ `
            <div class="parent">
                <View type="'list'" resModel="state.resModel" domain="state.domain" views="[[false, 'search']]" />
                <View type="'form'" resModel="state.resModel" resId="state.resId" withControlPanel="false" />
            </div>
        `;

        const env = await prepareEnv();
        await mount(Parent, target, { env });

        assert.containsN(target, ".o_view_controller", 2);
        assert.containsOnce(target, ".o_control_panel");
        assert.containsOnce(target, ".o_list_view");
        assert.containsOnce(target, ".o_form_view");

        // Change domain
        assert.containsN(target, ".o_data_row", 4);

        parentState.domain.push(["id", ">", 2]);
        await nextTick();

        assert.containsN(target, ".o_data_row", 2);

        // Change res id
        assert.strictEqual($(".o_form_view .o_field_char[name=foo]").text(), "frodo");

        parentState.resId = 2;
        await nextTick();

        assert.strictEqual($(".o_form_view .o_field_char[name=foo]").text(), "sam");
    });

    QUnit.test("Works inside of a component wrapper", async (assert) => {
        assert.expect(1);

        const legacyParent = new Widget();
        const wrapper = new ComponentWrapper(legacyParent, View, { type: "list", resModel: "hobbit" });

        await prepareEnv();

        await legacyParent.appendTo(target);
        await wrapper.mount(legacyParent.el);

        assert.containsN(legacyParent.el, ".o_data_row", 4);
    });

    QUnit.test("View adapter reactivity", async (assert) => {
        assert.expect(11);

        let parentState = reactive({ resId: 1 });
        let def = Promise.resolve();
        class Parent extends Component {
            setup() {
                this.state = useState(parentState);
            }
        }

        Parent.components = { View };
        Parent.template = xml/* xml */ `
            <div class="parent">
                <View type="'form'" resModel="'hobbit'" resId="state.resId" withControlPanel="false" />
            </div>
        `;

        const mockRPC = async (route, { method }) => {
            if (method === "read") {
                await def;
                assert.step("read");
            }
        };
        const env = await prepareEnv(mockRPC);
        await mount(Parent, target, { env });

        assert.containsOnce(target, ".o_view_controller");
        assert.strictEqual($(".o_form_view .o_field_char[name=foo]").text(), "frodo");
        assert.verifySteps(["read"]);

        def = makeDeferred();

        parentState.resId = 2;
        await nextTick();

        // View shouldn't be updated if the promise hasn't been resolved
        assert.containsOnce(target, ".o_view_controller");
        assert.strictEqual($(".o_form_view .o_field_char[name=foo]").text(), "frodo");
        assert.verifySteps([]);

        def.resolve();
        await nextTick();

        assert.containsOnce(target, ".o_view_controller");
        assert.strictEqual($(".o_form_view .o_field_char[name=foo]").text(), "sam");
        assert.verifySteps(["read"]);
    });

    QUnit.test("Given prop 'pushState' is correctly called", async (assert) => {
        assert.expect(3);

        class Parent extends Component {
            pushState() {
                assert.step("pushState");
            }
        }

        Parent.components = { View };
        Parent.template = xml/* xml */ `
            <div class="parent">
                <View type="'form'" resModel="'hobbit'" resId="1" withControlPanel="false" onPushState.bind="pushState" />
            </div>
        `;

        const env = await prepareEnv();

        assert.verifySteps([]);

        await mount(Parent, target, { env });

        assert.verifySteps(["pushState"]);
    });
});
