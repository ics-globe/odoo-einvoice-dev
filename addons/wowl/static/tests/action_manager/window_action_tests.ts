import * as QUnit from "qunit";
import $ from "jquery";
import { makeFakeUserService, nextTick } from "../helpers/index";
import { click, legacyExtraNextTick, TestConfig } from "../helpers/utility";
import { RPC } from "../../src/services/rpc";
import { getLegacy } from "../helpers/legacy";
import { clearUncommittedChanges } from "../../src/action_manager/action_manager";
import { actionRegistry } from "../../src/action_manager/action_registry";
import { viewRegistry } from "../../src/views/view_registry";
import { createWebClient, doAction, getActionManagerTestConfig, loadState } from "./helpers";
import {
  toggleFilterMenu,
  toggleMenuItem,
  toggleFavoriteMenu,
  toggleSaveFavorite,
  editFavoriteName,
  saveFavorite,
  switchView,
  toggleGroupByMenu,
  removeFacet,
} from "../helpers/control_panel";
import { Registry } from "../../src/core/registry";
import { CustomFavoriteItem } from "../../src/views/view_utils/favorite_menu/custom_favorite_item";

let testConfig: TestConfig;
// legacy stuff
let cpHelpers: any;
let testUtils: any;

QUnit.module("ActionManager", (hooks) => {
  hooks.before(() => {
    const legacy = getLegacy() as any;
    testUtils = legacy.testUtils;
    cpHelpers = testUtils.controlPanel;
  });

  // Remove this as soon as we drop the legacy support.
  // This is necessary as some tests add actions/views in the legacy registries,
  // which are in turned wrapped and added into the real wowl registries. We
  // add those actions/views in the test registries, and remove them from the
  // real ones (directly, as we don't need them in the test).
  const owner = Symbol("owner");
  hooks.beforeEach(() => {
    actionRegistry.on("UPDATE", owner, (payload) => {
      if (payload.operation === "add" && testConfig.actionRegistry) {
        testConfig.actionRegistry.add(payload.key, payload.value);
        actionRegistry.remove(payload.key);
      }
    });
    viewRegistry.on("UPDATE", owner, (payload) => {
      if (payload.operation === "add" && testConfig.viewRegistry) {
        testConfig.viewRegistry.add(payload.key, payload.value);
        viewRegistry.remove(payload.key);
      }
    });
  });
  hooks.afterEach(() => {
    actionRegistry.off("UPDATE", owner);
    viewRegistry.off("UPDATE", owner);
  });

  hooks.beforeEach(() => {
    testConfig = getActionManagerTestConfig();
  });

  QUnit.module("Window Actions");

  QUnit.test("can execute act_window actions from db ID", async function (assert) {
    assert.expect(7);

    const mockRPC: RPC = async (route, args) => {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });

    await doAction(webClient, 1);

    assert.containsOnce(document.body, ".o_control_panel", "should have rendered a control panel");
    assert.containsOnce(webClient, ".o_kanban_view", "should have rendered a kanban view");
    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "load_views",
      "/web/dataset/search_read",
    ]);

    webClient.destroy();
  });

  QUnit.skip("sidebar is present in list view", async function (assert) {
    // require list view to be expanded
    assert.expect(4);

    testConfig.serverData!.models!.partner.toolbar = {
      print: [{ name: "Print that record" }],
    };

    const mockRPC: RPC = async (route, args) => {
      if (args && args.method === "load_views") {
        assert.strictEqual(args.kwargs.options.toolbar, true, "should ask for toolbar information");
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });

    await doAction(webClient, 3);

    assert.containsNone(webClient, ".o_cp_action_menus");

    await testUtils.dom.clickFirst($(webClient.el!).find("input.custom-control-input"));
    assert.isVisible(
      $(webClient.el!).find('.o_cp_action_menus button.o_dropdown_toggler_btn:contains("Print")')[0]
    );
    assert.isVisible(
      $(webClient.el!).find(
        '.o_cp_action_menus button.o_dropdown_toggler_btn:contains("Action")'
      )[0]
    );

    webClient.destroy();
  });

  QUnit.test("can switch between views", async function (assert) {
    assert.expect(19);

    const mockRPC: RPC = async (route, args) => {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 3);

    assert.containsOnce(webClient, ".o_list_view", "should display the list view");

    // switch to kanban view
    await switchView(webClient.el!, "kanban");
    await legacyExtraNextTick();
    assert.containsNone(webClient, ".o_list_view", "should no longer display the list view");
    assert.containsOnce(webClient, ".o_kanban_view", "should display the kanban view");

    // switch back to list view
    await switchView(webClient.el!, "list");
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_list_view", "should display the list view");
    assert.containsNone(
      webClient.el!,
      ".o_kanban_view",
      "should no longer display the kanban view"
    );

    // open a record in form view
    await testUtils.dom.click(webClient.el!.querySelector(".o_list_view .o_data_row"));
    await legacyExtraNextTick();
    assert.containsNone(webClient, ".o_list_view", "should no longer display the list view");
    assert.containsOnce(webClient, ".o_form_view", "should display the form view");
    assert.strictEqual(
      $(webClient.el!).find(".o_field_widget[name=foo]").text(),
      "yop",
      "should have opened the correct record"
    );

    // go back to list view using the breadcrumbs
    await testUtils.dom.click(webClient.el!.querySelector(".o_control_panel .breadcrumb a"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_list_view", "should display the list view");
    assert.containsNone(webClient, ".o_form_view", "should no longer display the form view");

    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "load_views",
      "web_search_read", // list
      "/web/dataset/search_read", // kanban
      "web_search_read", // list
      "read", // form
      "web_search_read", // list
    ]);

    webClient.destroy();
  });

  QUnit.skip(
    "orderedBy in context is not propagated when executing another action",
    async function (assert) {
      // require list view to be expanded
      assert.expect(6);

      testConfig.serverData!.models!.partner.fields.foo.sortable = true;
      testConfig.serverData!.views!["partner,false,form"] = `
        <form>
          <header>
            <button name="8" string="Execute action" type="action"/>
          </header>
        </form>`;
      testConfig.serverData!.models!.partner.filters = [
        {
          id: 1,
          context: "{}",
          domain: "[]",
          sort: "[]",
          is_default: true,
          name: "My filter",
        },
      ];

      let searchReadCount = 1;
      const mockRPC: RPC = async (route, args) => {
        if (route === "/web/dataset/search_read") {
          args = args || {};
          if (searchReadCount === 1) {
            assert.strictEqual(args.model, "partner");
            assert.notOk(args.sort);
          }
          if (searchReadCount === 2) {
            assert.strictEqual(args.model, "partner");
            assert.strictEqual(args.sort, "foo ASC");
          }
          if (searchReadCount === 3) {
            assert.strictEqual(args.model, "pony");
            assert.notOk(args.sort);
          }
          searchReadCount += 1;
        }
      };
      const webClient = await createWebClient({ testConfig, mockRPC });
      await doAction(webClient, 3);

      // Sort records
      await testUtils.dom.click($(webClient.el!).find(".o_list_view th.o_column_sortable"));

      // Get to the form view of the model, on the first record
      await testUtils.dom.click($(webClient.el!).find(".o_data_cell:first"));
      await legacyExtraNextTick();

      // Execute another action by clicking on the button within the form
      await testUtils.dom.click($(webClient.el!).find("button[name=8]"));
      await legacyExtraNextTick();

      webClient.destroy();
    }
  );

  QUnit.test("breadcrumbs are updated when switching between views", async function (assert) {
    assert.expect(15);

    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);

    assert.containsOnce(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      "there should be one controller in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item").text(),
      "Partners",
      "breadcrumbs should display the display_name of the action"
    );

    // switch to kanban view
    await switchView(webClient.el!, "kanban");
    await legacyExtraNextTick();
    assert.containsOnce(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      "there should still be one controller in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item").text(),
      "Partners",
      "breadcrumbs should still display the display_name of the action"
    );

    // open a record in form view
    await testUtils.dom.click(webClient.el!.querySelector(".o_kanban_view .o_kanban_record"));
    await legacyExtraNextTick();
    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      2,
      "there should be two controllers in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item:last").text(),
      "First record"
    );

    // go back to kanban view using the breadcrumbs
    await testUtils.dom.click(webClient.el!.querySelector(".o_control_panel .breadcrumb a"));
    await legacyExtraNextTick();
    assert.containsOnce(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      "there should be one controller in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item").text(),
      "Partners",
      "breadcrumbs should display the display_name of the action"
    );

    // switch back to list view
    await switchView(webClient.el!, "list");
    await legacyExtraNextTick();
    assert.containsOnce(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      "there should still be one controller in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item").text(),
      "Partners",
      "breadcrumbs should still display the display_name of the action"
    );

    // open a record in form view
    await testUtils.dom.click(webClient.el!.querySelector(".o_list_view .o_data_row"));
    await legacyExtraNextTick();
    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      2,
      "there should be two controllers in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item:last").text(),
      "First record"
    );

    // go back to list view using the breadcrumbs
    await testUtils.dom.click(webClient.el!.querySelector(".o_control_panel .breadcrumb a"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_list_view", "should be back on list view");
    assert.containsOnce(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      "there should be one controller in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item").text(),
      "Partners",
      "breadcrumbs should display the display_name of the action"
    );

    webClient.destroy();
  });

  QUnit.test("switch buttons are updated when switching between views", async function (assert) {
    assert.expect(13);

    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);

    assert.containsN(
      webClient.el!,
      ".o_control_panel button.o_switch_view",
      2,
      "should have two switch buttons (list and kanban)"
    );
    assert.containsOnce(
      webClient.el!,
      ".o_control_panel button.o_switch_view.active",
      "should have only one active button"
    );
    assert.hasClass(
      webClient.el!.querySelector(".o_control_panel .o_switch_view") as HTMLElement,
      "o_list",
      "list switch button should be the first one"
    );
    assert.hasClass(
      webClient.el!.querySelector(".o_control_panel .o_switch_view.o_list") as HTMLElement,
      "active",
      "list should be the active view"
    );

    // switch to kanban view
    await switchView(webClient.el!, "kanban");
    await legacyExtraNextTick();
    assert.containsN(
      webClient.el!,
      ".o_control_panel .o_switch_view",
      2,
      "should still have two switch buttons (list and kanban)"
    );
    assert.containsOnce(
      webClient.el!,
      ".o_control_panel .o_switch_view.active",
      "should still have only one active button"
    );
    assert.hasClass(
      webClient.el!.querySelector(".o_control_panel .o_switch_view") as HTMLElement,
      "o_list",
      "list switch button should still be the first one"
    );
    assert.hasClass(
      webClient.el!.querySelector(".o_control_panel .o_switch_view.o_kanban") as HTMLElement,
      "active",
      "kanban should now be the active view"
    );

    // switch back to list view
    await switchView(webClient.el!, "list");
    await legacyExtraNextTick();
    assert.containsN(
      webClient.el!,
      ".o_control_panel .o_switch_view",
      2,
      "should still have two switch buttons (list and kanban)"
    );
    assert.hasClass(
      webClient.el!.querySelector(".o_control_panel .o_switch_view.o_list") as HTMLElement,
      "active",
      "list should now be the active view"
    );

    // open a record in form view
    await testUtils.dom.click(webClient.el!.querySelector(".o_list_view .o_data_row"));
    await legacyExtraNextTick();
    assert.containsNone(
      webClient.el!,
      ".o_control_panel .o_switch_view",
      "should not have any switch buttons"
    );

    // go back to list view using the breadcrumbs
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .breadcrumb a"));
    await legacyExtraNextTick();
    assert.containsN(
      webClient.el!,
      ".o_control_panel .o_switch_view",
      2,
      "should have two switch buttons (list and kanban)"
    );
    assert.hasClass(
      webClient.el!.querySelector(".o_control_panel .o_switch_view.o_list") as HTMLElement,
      "active",
      "list should be the active view"
    );

    webClient.destroy();
  });

  QUnit.skip("pager is updated when switching between views", async function (assert) {
    // Need work on list view
    assert.expect(10);

    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 4);

    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .o_pager_value").text(),
      "1-5",
      "value should be correct for kanban"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .o_pager_limit").text(),
      "5",
      "limit should be correct for kanban"
    );

    // switch to list view
    await switchView(webClient.el!, "list");
    await legacyExtraNextTick();
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .o_pager_value").text(),
      "1-3",
      "value should be correct for list"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .o_pager_limit").text(),
      "5",
      "limit should be correct for list"
    );

    // open a record in form view
    await testUtils.dom.click(webClient.el!.querySelector(".o_list_view .o_data_row"));
    await legacyExtraNextTick();
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .o_pager_value").text(),
      "1",
      "value should be correct for form"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .o_pager_limit").text(),
      "3",
      "limit should be correct for form"
    );

    // go back to list view using the breadcrumbs
    await testUtils.dom.click(webClient.el!.querySelector(".o_control_panel .breadcrumb a"));
    await legacyExtraNextTick();
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .o_pager_value").text(),
      "1-3",
      "value should be correct for list"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .o_pager_limit").text(),
      "5",
      "limit should be correct for list"
    );

    // switch back to kanban view
    await switchView(webClient.el!, "kanban");
    await legacyExtraNextTick();
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .o_pager_value").text(),
      "1-5",
      "value should be correct for kanban"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .o_pager_limit").text(),
      "5",
      "limit should be correct for kanban"
    );

    webClient.destroy();
  });

  QUnit.skip("domain is kept when switching between views", async function (assert) {
    // need work on export of search model state (through export callback?)
    assert.expect(5);

    testConfig.serverData!.actions![3].search_view_id = [1, "a custom search view"];

    const webClient = await createWebClient({ testConfig });

    await doAction(webClient, 3);
    assert.containsN(webClient, ".o_data_row", 5);

    // activate a domain
    await toggleFilterMenu(webClient.el!);
    await toggleMenuItem(webClient.el!, "Bar");
    await legacyExtraNextTick();
    assert.containsN(webClient, ".o_data_row", 2);

    // switch to kanban
    await switchView(webClient.el!, "kanban");
    await legacyExtraNextTick();
    assert.containsN(webClient, ".o_kanban_record:not(.o_kanban_ghost)", 2);

    // remove the domain
    await testUtils.dom.click(webClient.el!.querySelector(".o_searchview .o_facet_remove"));
    await legacyExtraNextTick();
    assert.containsN(webClient, ".o_kanban_record:not(.o_kanban_ghost)", 5);

    // switch back to list
    await switchView(webClient.el!, "list");
    await legacyExtraNextTick();
    assert.containsN(webClient, ".o_data_row", 5);

    webClient.destroy();
  });

  QUnit.test("there is no flickering when switching between views", async function (assert) {
    assert.expect(20);

    let def: any;
    const mockRPC: RPC = async (route, args) => {
      await def;
    };
    const webClient = await createWebClient({ testConfig, mockRPC });

    await doAction(webClient, 3);

    // switch to kanban view
    def = testUtils.makeTestPromise();
    await switchView(webClient.el!, "kanban");
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_list_view", "should still display the list view");
    assert.containsNone(webClient, ".o_kanban_view", "shouldn't display the kanban view yet");
    def.resolve();
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsNone(webClient, ".o_list_view", "shouldn't display the list view anymore");
    assert.containsOnce(webClient, ".o_kanban_view", "should now display the kanban view");

    // switch back to list view
    def = testUtils.makeTestPromise();
    await switchView(webClient.el!, "list");
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_kanban_view", "should still display the kanban view");
    assert.containsNone(webClient, ".o_list_view", "shouldn't display the list view yet");
    def.resolve();
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsNone(
      webClient.el!,
      ".o_kanban_view",
      "shouldn't display the kanban view anymore"
    );
    assert.containsOnce(webClient, ".o_list_view", "should now display the list view");

    // open a record in form view
    def = testUtils.makeTestPromise();
    await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_list_view", "should still display the list view");
    assert.containsNone(webClient, ".o_form_view", "shouldn't display the form view yet");
    assert.containsOnce(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      "there should still be one controller in the breadcrumbs"
    );
    def.resolve();
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsNone(webClient, ".o_list_view", "should no longer display the list view");
    assert.containsOnce(webClient, ".o_form_view", "should display the form view");
    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      2,
      "there should be two controllers in the breadcrumbs"
    );

    // go back to list view using the breadcrumbs
    def = testUtils.makeTestPromise();
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .breadcrumb a"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_form_view", "should still display the form view");
    assert.containsNone(webClient, ".o_list_view", "shouldn't display the list view yet");
    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      2,
      "there should still be two controllers in the breadcrumbs"
    );
    def.resolve();
    await testUtils.nextTick();
    await legacyExtraNextTick();
    assert.containsNone(webClient, ".o_form_view", "should no longer display the form view");
    assert.containsOnce(webClient, ".o_list_view", "should display the list view");
    assert.containsOnce(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      "there should be one controller in the breadcrumbs"
    );

    webClient.destroy();
  });

  QUnit.test("breadcrumbs are updated when display_name changes", async function (assert) {
    assert.expect(4);

    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);

    // open a record in form view
    await testUtils.dom.click(webClient.el!.querySelector(".o_list_view .o_data_row"));
    await legacyExtraNextTick();
    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      2,
      "there should be two controllers in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item:last").text(),
      "First record",
      "breadcrumbs should contain the display_name of the opened record"
    );

    // switch to edit mode and change the display_name
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .o_form_button_edit"));
    await testUtils.fields.editInput(
      webClient.el!.querySelector(".o_field_widget[name=display_name]"),
      "New name"
    );
    await testUtils.dom.click(webClient.el!.querySelector(".o_control_panel .o_form_button_save"));

    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      2,
      "there should still be two controllers in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item:last").text(),
      "New name",
      "breadcrumbs should contain the display_name of the opened record"
    );

    webClient.destroy();
  });

  QUnit.test('reverse breadcrumb works on accesskey "b"', async function (assert) {
    assert.expect(4);

    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);

    // open a record in form view
    await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
    await legacyExtraNextTick();
    await testUtils.dom.click(
      $(webClient.el!).find(".o_form_view button:contains(Execute action)")
    );
    await legacyExtraNextTick();

    assert.containsN(webClient, ".o_control_panel .breadcrumb li", 3);

    var $previousBreadcrumb = $(webClient.el!)
      .find(".o_control_panel .breadcrumb li.active")
      .prev();
    assert.strictEqual(
      $previousBreadcrumb.attr("accesskey"),
      "b",
      "previous breadcrumb should have accessKey 'b'"
    );
    await testUtils.dom.click($previousBreadcrumb);
    await legacyExtraNextTick();

    assert.containsN(webClient, ".o_control_panel .breadcrumb li", 2);

    var $previousBreadcrumb = $(webClient.el!)
      .find(".o_control_panel .breadcrumb li.active")
      .prev();
    assert.strictEqual(
      $previousBreadcrumb.attr("accesskey"),
      "b",
      "previous breadcrumb should have accessKey 'b'"
    );

    webClient.destroy();
  });

  QUnit.skip("reload previous controller when discarding a new record", async function (assert) {
    // require list view to be expanded
    assert.expect(9);

    const mockRPC: RPC = async (route, args) => {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 3);

    // create a new record
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .o_list_button_add"));
    assert.containsOnce(
      webClient.el!,
      ".o_form_view.o_form_editable",
      "should have opened the form view in edit mode"
    );

    // discard
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .o_form_button_cancel"));
    await legacyExtraNextTick();
    assert.containsOnce(
      webClient.el!,
      ".o_list_view",
      "should have switched back to the list view"
    );

    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "load_views",
      "web_search_read", // list
      "onchange", // form
      "web_search_read", // list
    ]);

    webClient.destroy();
  });

  QUnit.test("requests for execute_action of type object are handled", async function (assert) {
    assert.expect(11);

    testConfig.serviceRegistry!.add(
      "user",
      makeFakeUserService({
        context: Object.assign({}, { some_key: 2 } as any),
      }),
      true
    );

    const mockRPC: RPC = async (route, args) => {
      assert.step((args && args.method) || route);
      if (route === "/web/dataset/call_button") {
        assert.deepEqual(
          args,
          {
            args: [[1]],
            kwargs: { context: { some_key: 2 } },
            method: "object",
            model: "partner",
          },
          "should call route with correct arguments"
        );
        const record = testConfig.serverData!.models!.partner.records.find(
          (r) => r.id === args!.args[0][0]
        );
        record!.foo = "value changed";
        return Promise.resolve(false);
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 3);

    // open a record in form view
    await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
    await legacyExtraNextTick();
    assert.strictEqual(
      $(webClient.el!).find(".o_field_widget[name=foo]").text(),
      "yop",
      "check initial value of 'yop' field"
    );

    // click on 'Call method' button (should call an Object method)
    await testUtils.dom.click($(webClient.el!).find(".o_form_view button:contains(Call method)"));
    await legacyExtraNextTick();
    assert.strictEqual(
      $(webClient.el!).find(".o_field_widget[name=foo]").text(),
      "value changed",
      "'yop' has been changed by the server, and should be updated in the UI"
    );

    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "load_views",
      "web_search_read", // list for action 3
      "read", // form for action 3
      "object", // click on 'Call method' button
      "read", // re-read form view
    ]);

    webClient.destroy();
  });

  QUnit.test(
    "requests for execute_action of type object: disable buttons (2)",
    async function (assert) {
      assert.expect(6);

      testConfig.serverData!.views!["pony,44,form"] = `
    <form>
    <field name="name"/>
    <button string="Cancel" class="cancel-btn" special="cancel"/>
    </form>`;
      testConfig.serverData!.actions![4] = {
        id: 4,
        name: "Create a Partner",
        res_model: "pony",
        target: "new",
        type: "ir.actions.act_window",
        views: [[44, "form"]],
      };
      const def = testUtils.makeTestPromise();
      const mockRPC: RPC = async (route, args) => {
        if (args!.method === "onchange") {
          // delay the opening of the dialog
          await def;
        }
      };
      const webClient = await createWebClient({ testConfig, mockRPC });
      await doAction(webClient, 3);
      assert.containsOnce(webClient.el!, ".o_list_view");

      // open first record in form view
      await testUtils.dom.click(webClient.el!.querySelector(".o_list_view .o_data_row"));
      await legacyExtraNextTick();
      assert.containsOnce(webClient.el!, ".o_form_view");

      // click on 'Execute action', to execute action 4 in a dialog
      await testUtils.dom.click(webClient.el!.querySelector('.o_form_view button[name="4"]'));
      await legacyExtraNextTick();
      assert.ok(
        (webClient.el!.querySelector(".o_cp_buttons .o_form_button_edit")! as any).disabled,
        "control panel buttons should be disabled"
      );

      def.resolve();
      await nextTick();
      await legacyExtraNextTick();
      assert.containsOnce(webClient.el!, ".modal .o_form_view");
      assert.notOk(
        (webClient.el!.querySelector(".o_cp_buttons .o_form_button_edit")! as any).disabled,
        "control panel buttons should have been re-enabled"
      );

      await testUtils.dom.click(webClient.el!.querySelector(".modal .cancel-btn"));
      await legacyExtraNextTick();
      assert.notOk(
        (webClient.el!.querySelector(".o_cp_buttons .o_form_button_edit")! as any).disabled,
        "control panel buttons should still be enabled"
      );

      webClient.destroy();
    }
  );

  QUnit.test(
    "requests for execute_action of type object raises error: re-enables buttons",
    async function (assert) {
      assert.expect(3);

      const mockRPC: RPC = async (route, args) => {
        if (route === "/web/dataset/call_button") {
          return Promise.reject();
        }
      };
      const webClient = await createWebClient({ testConfig, mockRPC });

      await doAction(webClient, 3, { viewType: "form" });
      assert.containsOnce(webClient.el!, ".o_form_view");

      // click on 'Execute action', to execute action 4 in a dialog
      testUtils.dom.click(webClient.el!.querySelector('.o_form_view button[name="object"]'));
      assert.ok((webClient.el!.querySelector(".o_cp_buttons button")! as any).disabled);
      await nextTick();
      await legacyExtraNextTick();
      assert.notOk((webClient.el!.querySelector(".o_cp_buttons button")! as any).disabled);
      webClient.destroy();
    }
  );

  QUnit.test(
    "requests for execute_action of type object raises error in modal: re-enables buttons",
    async function (assert) {
      assert.expect(5);

      testConfig.serverData!.views!["partner,false,form"] = `
        <form>
          <field name="display_name"/>
          <footer>
            <button name="object" string="Call method" type="object"/>
          </footer>
        </form>
      `;

      const mockRPC: RPC = async (route, args) => {
        if (route === "/web/dataset/call_button") {
          return Promise.reject();
        }
      };
      const webClient = await createWebClient({ testConfig, mockRPC });
      await doAction(webClient, 5);
      assert.containsOnce(webClient.el!, ".modal .o_form_view");

      testUtils.dom.click(webClient.el!.querySelector('.modal footer button[name="object"]')!);
      assert.containsOnce(webClient.el!, ".modal .o_form_view");
      assert.ok(
        (webClient.el!.querySelector(".modal footer button") as HTMLButtonElement).disabled
      );
      await testUtils.nextTick();
      await legacyExtraNextTick();
      assert.containsOnce(webClient.el!, ".modal .o_form_view");
      assert.notOk(
        (webClient.el!.querySelector(".modal footer button") as HTMLButtonElement).disabled
      );
      webClient.destroy();
    }
  );

  QUnit.test("requests for execute_action of type action are handled", async function (assert) {
    assert.expect(12);

    const mockRPC: RPC = async (route, args) => {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 3);

    // open a record in form view
    await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
    await legacyExtraNextTick();

    // click on 'Execute action' button (should execute an action)
    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      2,
      "there should be two parts in the breadcrumbs"
    );
    await testUtils.dom.click(
      $(webClient.el!).find(".o_form_view button:contains(Execute action)")
    );
    await legacyExtraNextTick();
    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      3,
      "the returned action should have been stacked over the previous one"
    );
    assert.containsOnce(
      webClient.el!,
      ".o_kanban_view",
      "the returned action should have been executed"
    );

    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "load_views",
      "web_search_read", // list for action 3
      "read", // form for action 3
      "/web/action/load", // click on 'Execute action' button
      "load_views",
      "/web/dataset/search_read", // kanban for action 4
    ]);

    webClient.destroy();
  });

  QUnit.test("execute smart button and back", async function (assert) {
    assert.expect(8);

    const mockRPC: RPC = async (route, args) => {
      if (args!.method === "read") {
        assert.notOk("default_partner" in args!.kwargs.context);
      }
      if (route === "/web/dataset/search_read") {
        assert.strictEqual(args!.context.default_partner, 2);
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });

    await doAction(webClient, 24);
    assert.containsOnce(webClient.el!, ".o_form_view");
    assert.containsN(webClient.el!, ".o_form_buttons_view button:not([disabled])", 2);

    await testUtils.dom.click(webClient.el!.querySelector(".oe_stat_button"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient.el!, ".o_kanban_view");

    await testUtils.dom.click(webClient.el!.querySelector(".breadcrumb-item"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient.el!, ".o_form_view");
    assert.containsN(webClient.el!, ".o_form_buttons_view button:not([disabled])", 2);
    webClient.destroy();
  });

  QUnit.test("execute smart button and fails", async function (assert) {
    assert.expect(12);

    const mockRPC: RPC = async (route, args) => {
      assert.step(route);
      if (route === "/web/dataset/search_read") {
        return Promise.reject();
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });

    await doAction(webClient, 24);
    assert.containsOnce(webClient.el!, ".o_form_view");
    assert.containsN(webClient.el!, ".o_form_buttons_view button:not([disabled])", 2);

    await testUtils.dom.click(webClient.el!.querySelector(".oe_stat_button"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient.el!, ".o_form_view");
    assert.containsN(webClient.el!, ".o_form_buttons_view button:not([disabled])", 2);

    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "/web/dataset/call_kw/partner/load_views",
      "/web/dataset/call_kw/partner/read",
      "/web/action/load",
      "/web/dataset/call_kw/partner/load_views",
      "/web/dataset/search_read",
    ]);
    webClient.destroy();
  });

  QUnit.test(
    "requests for execute_action of type object: disable buttons",
    async function (assert) {
      assert.expect(2);

      let def: any;
      const mockRPC: RPC = async (route, args) => {
        if (route === "/web/dataset/call_button") {
          return Promise.resolve(false);
        } else if (args && args.method === "read") {
          await def; // block the 'read' call
        }
      };
      const webClient = await createWebClient({ testConfig, mockRPC });
      await doAction(webClient, 3);

      // open a record in form view
      await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
      await legacyExtraNextTick();

      // click on 'Call method' button (should call an Object method)
      def = testUtils.makeTestPromise();
      await testUtils.dom.click($(webClient.el!).find(".o_form_view button:contains(Call method)"));
      await legacyExtraNextTick();

      // Buttons should be disabled
      assert.strictEqual(
        $(webClient.el!).find(".o_form_view button:contains(Call method)").attr("disabled"),
        "disabled",
        "buttons should be disabled"
      );

      // Release the 'read' call
      def.resolve();
      await testUtils.nextTick();
      await legacyExtraNextTick();

      // Buttons should be enabled after the reload
      assert.strictEqual(
        $(webClient.el!).find(".o_form_view button:contains(Call method)").attr("disabled"),
        undefined,
        "buttons should not be disabled anymore"
      );

      webClient.destroy();
    }
  );

  QUnit.test("can open different records from a multi record view", async function (assert) {
    assert.expect(12);

    const mockRPC: RPC = async (route, args) => {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 3);

    // open the first record in form view
    await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
    await legacyExtraNextTick();
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item:last").text(),
      "First record",
      "breadcrumbs should contain the display_name of the opened record"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_field_widget[name=foo]").text(),
      "yop",
      "should have opened the correct record"
    );

    // go back to list view using the breadcrumbs
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .breadcrumb a"));
    await legacyExtraNextTick();

    // open the second record in form view
    await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:nth(1)"));
    await legacyExtraNextTick();
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item:last").text(),
      "Second record",
      "breadcrumbs should contain the display_name of the opened record"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_field_widget[name=foo]").text(),
      "blip",
      "should have opened the correct record"
    );

    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load",
      "load_views",
      "web_search_read", // list
      "read", // form
      "web_search_read", // list
      "read", // form
    ]);

    webClient.destroy();
  });

  QUnit.test("restore previous view state when switching back", async function (assert) {
    assert.expect(5);

    testConfig.serverData!.actions![3].views.unshift([false, "graph"]);
    testConfig.serverData!.views!["partner,false,graph"] = "<graph/>";

    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);

    assert.hasClass(
      $(webClient.el!).find(".o_control_panel  .fa-bar-chart-o")[0],
      "active",
      "bar chart button is active"
    );
    assert.doesNotHaveClass(
      $(webClient.el!).find(".o_control_panel  .fa-area-chart")[0],
      "active",
      "line chart button is not active"
    );

    // display line chart
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel  .fa-area-chart"));
    await legacyExtraNextTick();
    assert.hasClass(
      $(webClient.el!).find(".o_control_panel  .fa-area-chart")[0],
      "active",
      "line chart button is now active"
    );

    // switch to kanban and back to graph view
    await switchView(webClient.el!, "kanban");
    await legacyExtraNextTick();
    assert.containsNone(
      webClient.el!,
      ".o_control_panel  .fa-area-chart",
      "graph buttons are no longer in control panel"
    );

    await switchView(webClient.el!, "graph");
    await legacyExtraNextTick();
    assert.hasClass(
      $(webClient.el!).find(".o_control_panel  .fa-area-chart")[0],
      "active",
      "line chart button is still active"
    );
    webClient.destroy();
  });

  QUnit.test("view switcher is properly highlighted in graph view", async function (assert) {
    assert.expect(4);

    testConfig.serverData!.actions![3].views.splice(1, 1, [false, "graph"]);
    testConfig.serverData!.views!["partner,false,graph"] = "<graph/>";

    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);

    assert.hasClass(
      $(webClient.el!).find(".o_control_panel .o_switch_view.o_list")[0],
      "active",
      "list button in control panel is active"
    );
    assert.doesNotHaveClass(
      $(webClient.el!).find(".o_control_panel .o_switch_view.o_graph")[0],
      "active",
      "graph button in control panel is not active"
    );

    // switch to graph view
    await switchView(webClient.el!, "graph");
    await legacyExtraNextTick();
    assert.doesNotHaveClass(
      $(webClient.el!).find(".o_control_panel .o_switch_view.o_list")[0],
      "active",
      "list button in control panel is not active"
    );
    assert.hasClass(
      $(webClient.el!).find(".o_control_panel .o_switch_view.o_graph")[0],
      "active",
      "graph button in control panel is active"
    );
    webClient.destroy();
  });

  QUnit.skip("can interact with search view", async function (assert) {
    // need more work on list view (grouped list view)
    assert.expect(2);

    testConfig.serverData!.views!["partner,false,search"] = `
      <search>
        <group>
          <filter name="foo" string="Foo" context="{'group_by': 'foo'}"/>
        </group>
      </search>`;

    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);

    assert.doesNotHaveClass(
      $(webClient.el!).find(".o_list_table")[0],
      "o_list_table_grouped",
      "list view is not grouped"
    );

    await toggleGroupByMenu(webClient.el!);
    await toggleMenuItem(webClient.el!, "Foo");

    assert.hasClass(
      $(webClient.el!).find(".o_list_table")[0],
      "o_list_table_grouped",
      "list view is now grouped"
    );

    webClient.destroy();
  });

  QUnit.test("can open a many2one external window", async function (assert) {
    assert.expect(9);

    testConfig.serverData!.models!.partner.records[0].bar = 2;
    testConfig.serverData!.views!["partner,false,search"] = `
      <search>
        <group>
          <filter name="foo" string="foo" context="{'group_by': 'foo'}"/>
        </group>
      </search>`;
    testConfig.serverData!.views!["partner,false,form"] = `
      <form>
        <field name="foo"/>
        <field name="bar"/>
      </form>`;

    const mockRPC: RPC = async (route, args) => {
      assert.step(route);
      if (args && args.method === "get_formview_id") {
        return Promise.resolve(false);
      }
    };

    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 3);

    // open first record in form view
    await testUtils.dom.click($(webClient.el!).find(".o_data_row:first"));
    await legacyExtraNextTick();
    // click on edit
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .o_form_button_edit"));
    await legacyExtraNextTick();

    // click on external button for m2o
    await testUtils.dom.click($(webClient.el!).find(".o_external_button"));
    await legacyExtraNextTick();

    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load", // initial load action
      "/web/dataset/call_kw/partner/load_views", // load views
      "/web/dataset/call_kw/partner/web_search_read", // read list view data
      "/web/dataset/call_kw/partner/read", // read form view data
      "/web/dataset/call_kw/partner/get_formview_id", // get form view id
      "/web/dataset/call_kw/partner", // load form view for modal
      "/web/dataset/call_kw/partner/read", // read data for m2o record
    ]);
    webClient.destroy();
  });

  QUnit.test('ask for confirmation when leaving a "dirty" view', async function (assert) {
    assert.expect(4);

    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 4);

    // open record in form view
    await testUtils.dom.click($(webClient.el!).find(".o_kanban_record:first")[0]);
    await legacyExtraNextTick();

    // edit record
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel button.o_form_button_edit"));
    await testUtils.fields.editInput($(webClient.el!).find('input[name="foo"]'), "pinkypie");

    // go back to kanban view
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .breadcrumb-item:first a"));
    await legacyExtraNextTick();

    assert.strictEqual(
      $(".modal .modal-body").text(),
      "The record has been modified, your changes will be discarded. Do you want to proceed?",
      "should display a modal dialog to confirm discard action"
    );

    // cancel
    await testUtils.dom.click($(".modal .modal-footer button.btn-secondary"));
    await legacyExtraNextTick();

    assert.containsOnce(webClient, ".o_form_view", "should still be in form view");

    // go back again to kanban view
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .breadcrumb-item:first a"));
    await legacyExtraNextTick();

    // confirm discard
    await testUtils.dom.click($(".modal .modal-footer button.btn-primary"));
    await legacyExtraNextTick();

    assert.containsNone(webClient, ".o_form_view", "should no longer be in form view");
    assert.containsOnce(webClient, ".o_kanban_view", "should be in kanban view");

    webClient.destroy();
  });

  QUnit.test("limit set in action is passed to each created controller", async function (assert) {
    assert.expect(2);

    testConfig.serverData!.actions![3].limit = 2;
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);

    assert.containsN(webClient, ".o_data_row", 2);

    // switch to kanban view
    await switchView(webClient.el!, "kanban");
    await legacyExtraNextTick();

    assert.containsN(webClient, ".o_kanban_record:not(.o_kanban_ghost)", 2);

    webClient.destroy();
  });

  QUnit.test("go back to a previous action using the breadcrumbs", async function (assert) {
    assert.expect(10);

    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);

    // open a record in form view
    await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
    await legacyExtraNextTick();
    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      2,
      "there should be two controllers in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item:last").text(),
      "First record",
      "breadcrumbs should contain the display_name of the opened record"
    );

    // push another action on top of the first one, and come back to the form view
    await doAction(webClient, 4);
    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      3,
      "there should be three controllers in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item:last").text(),
      "Partners Action 4",
      "breadcrumbs should contain the name of the current action"
    );
    // go back using the breadcrumbs
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .breadcrumb a:nth(1)"));
    await legacyExtraNextTick();
    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      2,
      "there should be two controllers in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item:last").text(),
      "First record",
      "breadcrumbs should contain the display_name of the opened record"
    );

    // push again the other action on top of the first one, and come back to the list view
    await doAction(webClient, 4);
    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      3,
      "there should be three controllers in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item:last").text(),
      "Partners Action 4",
      "breadcrumbs should contain the name of the current action"
    );
    // go back using the breadcrumbs
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .breadcrumb a:first"));
    await legacyExtraNextTick();
    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      1,
      "there should be one controller in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item:last").text(),
      "Partners",
      "breadcrumbs should contain the name of the current action"
    );

    webClient.destroy();
  });

  QUnit.test(
    "form views are restored in readonly when coming back in breadcrumbs",
    async function (assert) {
      assert.expect(2);

      const webClient = await createWebClient({ testConfig });
      await doAction(webClient, 3);

      // open a record in form view
      await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
      await legacyExtraNextTick();
      // switch to edit mode
      await testUtils.dom.click($(webClient.el!).find(".o_control_panel .o_form_button_edit"));
      await legacyExtraNextTick();

      assert.hasClass($(webClient.el!).find(".o_form_view")[0], "o_form_editable");
      // do some other action
      await doAction(webClient, 4);
      // go back to form view
      await testUtils.dom.clickLast($(webClient.el!).find(".o_control_panel .breadcrumb a"));
      await legacyExtraNextTick();
      assert.hasClass($(webClient.el!).find(".o_form_view")[0], "o_form_readonly");

      webClient.destroy();
    }
  );

  QUnit.skip("honor group_by specified in actions context", async function (assert) {
    // need more work on list view (grouped list view)
    assert.expect(5);

    testConfig.serverData!.actions![3].context = "{'group_by': 'bar'}";
    testConfig.serverData!.views!["partner,false,search"] = `
      <search>
        <group>
          <filter name="foo" string="foo" context="{'group_by': 'foo'}"/>
        </group>
      </search>`;

    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);

    assert.containsOnce(webClient, ".o_list_table_grouped", "should be grouped");
    assert.containsN(
      webClient.el!,
      ".o_group_header",
      2,
      "should be grouped by 'bar' (two groups) at first load"
    );

    // groupby 'foo' using the searchview
    await toggleGroupByMenu(webClient.el!);
    await toggleMenuItem(webClient.el!, "Foo");

    assert.containsN(
      webClient.el!,
      ".o_group_header",
      5,
      "should be grouped by 'foo' (five groups)"
    );

    // remove the groupby in the searchview
    await removeFacet(webClient.el!);

    assert.containsOnce(webClient, ".o_list_table_grouped", "should still be grouped");
    assert.containsN(
      webClient.el!,
      ".o_group_header",
      2,
      "should be grouped by 'bar' (two groups) at reload"
    );

    webClient.destroy();
  });

  QUnit.test("switch request to unknown view type", async function (assert) {
    assert.expect(8);

    testConfig.serverData!.actions![33] = {
      id: 33,
      name: "Partners",
      res_model: "partner",
      type: "ir.actions.act_window",
      views: [
        [false, "list"],
        [1, "kanban"],
      ], // no form view
    };

    const mockRPC: RPC = async (route, args) => {
      assert.step((args && args.method) || route);
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 33);

    assert.containsOnce(webClient, ".o_list_view", "should display the list view");

    // try to open a record in a form view
    await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
    assert.containsOnce(webClient, ".o_list_view", "should still display the list view");
    assert.containsNone(webClient, ".o_form_view", "should not display the form view");

    assert.verifySteps(["/wowl/load_menus", "/web/action/load", "load_views", "web_search_read"]);

    webClient.destroy();
  });

  QUnit.skip("save current search", async function (assert) {
    // move it in some "AbstractView" + "CP" test file
    assert.expect(4);

    // const onSaveParams = ListView.onSaveParams;
    /** @todo don't like this --> to change */
    // ListView.onSaveParams = () => {
    //   return { context: { shouldBeInFilterContext: true } };
    // };

    testConfig.serverData!.actions![33] = {
      id: 33,
      context: {
        shouldNotBeInFilterContext: false,
      },
      name: "Partners",
      res_model: "partner",
      search_view_id: [1, "a custom search view"],
      type: "ir.actions.act_window",
      views: [[false, "list"]],
    };

    testConfig.favoriteMenuRegistry = new Registry();
    testConfig.favoriteMenuRegistry.add("favorite-generator-menu", CustomFavoriteItem);

    const mockRPC: RPC = async (route, args) => {
      if (args && args.method === "create_or_replace") {
        const filter = args.args[0];
        assert.strictEqual(filter.domain, `[("bar", "=", 1)]`, "should save the correct domain");
        const expectedContext = {
          group_by: [], // default groupby is an empty list
          shouldBeInFilterContext: true,
        };
        assert.deepEqual(filter.context, expectedContext, "should save the correct context");
        return 4; // favorite server id
      }
    };

    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 33);

    assert.containsN(webClient, ".o_data_row", 5, "should contain 5 records");

    // filter on bar
    await toggleFilterMenu(webClient.el!);
    await toggleMenuItem(webClient.el!, "Bar");

    assert.containsN(webClient, ".o_data_row", 2);

    // save filter
    await toggleFavoriteMenu(webClient.el!);
    await toggleSaveFavorite(webClient.el!);
    await editFavoriteName(webClient.el!, "some name");
    await saveFavorite(webClient.el!);
    await legacyExtraNextTick();

    // ListView.onSaveParams = onSaveParams;
    webClient.destroy();
  });

  QUnit.skip(
    "list with default_order and favorite filter with no orderedBy",
    async function (assert) {
      // require list view to be expanded
      assert.expect(5);

      testConfig.serverData!.views!["partner,1,list"] =
        '<tree default_order="foo desc"><field name="foo"/></tree>';
      testConfig.serverData!.actions![100] = {
        id: 100,
        name: "Partners",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
          [1, "list"],
          [false, "form"],
        ],
      };
      testConfig.serverData!.models!.partner.filters = [
        {
          name: "favorite filter",
          id: 5,
          context: "{}",
          sort: "[]",
          domain: '[("bar", "=", 1)]',
          is_default: false,
        },
      ];

      const webClient = await createWebClient({ testConfig });
      await doAction(webClient, 100);

      assert.strictEqual(
        $(webClient.el!).find(".o_list_view tr.o_data_row .o_data_cell").text(),
        "zoupyopplopgnapblip",
        "record should be in descending order as default_order applies"
      );

      await cpHelpers.toggleFavoriteMenu(webClient.el!);
      await cpHelpers.toggleMenuItem(webClient.el!, "favorite filter");
      await legacyExtraNextTick();

      assert.strictEqual(
        $(webClient.el!).find(".o_control_panel .o_facet_values").text().trim(),
        "favorite filter",
        "favorite filter should be applied"
      );
      assert.strictEqual(
        $(webClient.el!).find(".o_list_view tr.o_data_row .o_data_cell").text(),
        "gnapblip",
        "record should still be in descending order after default_order applied"
      );

      // go to formview and come back to listview
      await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
      await legacyExtraNextTick();
      await testUtils.dom.click($(webClient.el!).find(".o_control_panel .breadcrumb a:eq(0)"));
      await legacyExtraNextTick();
      assert.strictEqual(
        $(webClient.el!).find(".o_list_view tr.o_data_row .o_data_cell").text(),
        "gnapblip",
        "order of records should not be changed, while coming back through breadcrumb"
      );

      // remove filter
      await cpHelpers.removeFacet(webClient.el!, 0);
      await legacyExtraNextTick();
      assert.strictEqual(
        $(webClient.el!).find(".o_list_view tr.o_data_row .o_data_cell").text(),
        "zoupyopplopgnapblip",
        "order of records should not be changed, after removing current filter"
      );

      webClient.destroy();
    }
  );

  QUnit.test(
    "search menus are still available when switching between actions",
    async function (assert) {
      assert.expect(3);

      const webClient = await createWebClient({ testConfig });

      await doAction(webClient, 1);
      assert.isVisible(
        webClient.el!.querySelector(".o_search_options .o_dropdown.o_filter_menu") as HTMLElement,
        "the search options should be available"
      );

      await doAction(webClient, 3);
      assert.isVisible(
        webClient.el!.querySelector(".o_search_options .o_dropdown.o_filter_menu") as HTMLElement,
        "the search options should be available"
      );

      // go back using the breadcrumbs
      await testUtils.dom.click($(webClient.el!).find(".o_control_panel .breadcrumb a:first"));
      await legacyExtraNextTick();
      assert.isVisible(
        webClient.el!.querySelector(".o_search_options .o_dropdown.o_filter_menu") as HTMLElement,
        "the search options should be available"
      );

      webClient.destroy();
    }
  );

  QUnit.test("current act_window action is stored in session_storage", async function (assert) {
    assert.expect(1);

    const expectedAction = {
      ...testConfig.serverData!.actions![3],
      context: {
        lang: "en",
        uid: 7,
        tz: "taht",
      },
    };
    const sessionStorage = testConfig.browser!.sessionStorage;
    testConfig.browser!.sessionStorage = Object.assign(Object.create(sessionStorage!), {
      setItem(k: any, value: any) {
        assert.strictEqual(
          value,
          JSON.stringify(expectedAction),
          "should store the executed action in the sessionStorage"
        );
      },
    });
    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 3);
    webClient.destroy();
  });

  QUnit.test(
    "store evaluated context of current action in session_storage",
    async function (assert) {
      // this test ensures that we don't store stringified instances of
      // CompoundContext in the session_storage, as they would be meaningless
      // once restored
      assert.expect(1);

      const expectedAction = {
        ...testConfig.serverData!.actions![4],
        context: {
          lang: "en",
          uid: 7,
          tz: "taht",
          active_model: "partner",
          active_id: 1,
          active_ids: [1],
        },
      };
      let checkSessionStorage = false;

      const sessionStorage = testConfig.browser!.sessionStorage;
      testConfig.browser!.sessionStorage = Object.assign(Object.create(sessionStorage!), {
        setItem(k: any, value: any) {
          if (checkSessionStorage) {
            assert.strictEqual(
              value,
              JSON.stringify(expectedAction),
              "should store the executed action in the sessionStorage"
            );
          }
        },
      });
      const webClient = await createWebClient({ testConfig });

      // execute an action and open a record in form view
      await doAction(webClient, 3);
      await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
      await legacyExtraNextTick();

      // click on 'Execute action' button (it executes an action with a CompoundContext as context)
      checkSessionStorage = true;
      await testUtils.dom.click(
        $(webClient.el!).find(".o_form_view button:contains(Execute action)")
      );
      await legacyExtraNextTick();

      webClient.destroy();
    }
  );

  QUnit.test("destroy action with lazy loaded controller", async function (assert) {
    assert.expect(6);

    const webClient = await createWebClient({ testConfig });
    await loadState(webClient, {
      action: "3",
      id: "2",
      view_type: "form",
    });
    assert.containsNone(webClient, ".o_list_view");
    assert.containsOnce(webClient, ".o_form_view");
    assert.containsN(
      webClient.el!,
      ".o_control_panel .breadcrumb-item",
      2,
      "there should be two controllers in the breadcrumbs"
    );
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item:last").text(),
      "Second record",
      "breadcrumbs should contain the display_name of the opened record"
    );

    await doAction(webClient, 1, { clearBreadcrumbs: true });

    assert.containsNone(webClient, ".o_form_view");
    assert.containsOnce(webClient, ".o_kanban_view");

    webClient.destroy();
  });

  QUnit.skip("execute action from dirty, new record, and come back", async function (assert) {
    // need more work on list view (button create)
    assert.expect(18);

    testConfig.serverData!.models!.partner.fields.bar.default = 1;
    testConfig.serverData!.views!["partner,false,form"] = `
      <form>
        <field name="foo"/>
        <field name="bar" readonly="1"/>
      </form>`;

    const mockRPC: RPC = async (route, args) => {
      assert.step((args && args.method) || route);
      if (args && args.method === "get_formview_action") {
        return Promise.resolve({
          res_id: 1,
          res_model: "partner",
          type: "ir.actions.act_window",
          views: [[false, "form"]],
        });
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });

    // execute an action and create a new record
    await doAction(webClient, 3);
    await testUtils.dom.click($(webClient.el!).find(".o_list_button_add"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_form_view.o_form_editable");
    assert.containsOnce(webClient, ".o_form_uri:contains(First record)");
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item").text(),
      "PartnersNew"
    );

    // set form view dirty and open m2o record
    await testUtils.fields.editInput($(webClient.el!).find("input[name=foo]"), "val");
    await testUtils.dom.click($(webClient.el!).find(".o_form_uri:contains(First record)"));
    await legacyExtraNextTick();
    assert.containsOnce(document.body, ".modal"); // confirm discard dialog

    // confirm discard changes
    await testUtils.dom.click($(".modal .modal-footer .btn-primary"));
    await legacyExtraNextTick();

    assert.containsOnce(webClient, ".o_form_view.o_form_readonly");
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item").text(),
      "PartnersNewFirst record"
    );

    // go back to New using the breadcrumbs
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .breadcrumb-item:nth(1) a"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_form_view.o_form_editable");
    assert.strictEqual(
      $(webClient.el!).find(".o_control_panel .breadcrumb-item").text(),
      "PartnersNew"
    );

    assert.verifySteps([
      "/wowl/load_menus",
      "/web/action/load", // action 3
      "load_views", // views of action 3
      "/web/dataset/search_read", // list
      "onchange", // form (create)
      "get_formview_action", // click on m2o
      "load_views", // form view of dynamic action
      "read", // form
      "onchange", // form (create)
    ]);

    webClient.destroy();
  });

  QUnit.test("execute a contextual action from a form view", async function (assert) {
    assert.expect(4);

    const contextualAction = testConfig.serverData!.actions![8];
    contextualAction.context = "{}"; // need a context to evaluate
    testConfig.serverData!.models!.partner.toolbar = {
      action: [contextualAction],
      print: [],
    };

    const mockRPC: RPC = async (route, args) => {
      if (args && args.method === "load_views" && args.model === "partner") {
        assert.strictEqual(args.kwargs.options.toolbar, true, "should ask for toolbar information");
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });

    // execute an action and open a record
    await doAction(webClient, 3);
    assert.containsOnce(webClient, ".o_list_view");
    await testUtils.dom.click($(webClient.el!).find(".o_data_row:first"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_form_view");

    // execute the custom action from the action menu
    await cpHelpers.toggleActionMenu(webClient.el!);
    await cpHelpers.toggleMenuItem(webClient.el!, "Favorite Ponies");
    await legacyExtraNextTick();
    assert.containsOnce(webClient, ".o_list_view");

    webClient.destroy();
  });

  QUnit.test("go back to action with form view as main view, and res_id", async function (assert) {
    assert.expect(7);

    testConfig.serverData!.actions![999] = {
      id: 999,
      name: "Partner",
      res_model: "partner",
      type: "ir.actions.act_window",
      res_id: 2,
      views: [[44, "form"]],
    };
    testConfig.serverData!.views!["partner,44,form"] = '<form><field name="m2o"/></form>';

    const mockRPC: RPC = async (route, args) => {
      if (args!.method === "get_formview_action") {
        return Promise.resolve({
          res_id: 3,
          res_model: "partner",
          type: "ir.actions.act_window",
          views: [[false, "form"]],
        });
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });

    await doAction(webClient, 999);

    assert.containsOnce(webClient.el!, ".o_form_view");
    assert.hasClass(webClient.el!.querySelector(".o_form_view")! as HTMLElement, "o_form_readonly");
    assert.strictEqual(
      webClient.el!.querySelector(".o_control_panel .breadcrumb")!.textContent,
      "Second record"
    );

    // push another action in the breadcrumb
    await testUtils.dom.click($(webClient.el!).find(".o_form_uri:contains(Third record)"));
    await legacyExtraNextTick();
    assert.strictEqual(
      webClient.el!.querySelector(".o_control_panel .breadcrumb")!.textContent,
      "Second recordThird record"
    );

    // go back to the form view
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .breadcrumb a:first"));
    await legacyExtraNextTick();

    assert.containsOnce(webClient.el!, ".o_form_view");
    assert.hasClass(webClient.el!.querySelector(".o_form_view")! as HTMLElement, "o_form_readonly");
    assert.strictEqual(
      webClient.el!.querySelector(".o_control_panel .breadcrumb-item")!.textContent,
      "Second record"
    );

    webClient.destroy();
  });

  QUnit.skip("open a record, come back, and create a new record", async function (assert) {
    // need more work on list view (button create)
    assert.expect(7);

    const webClient = await createWebClient({ testConfig });

    // execute an action and open a record
    await doAction(webClient, 3);
    assert.containsOnce(webClient.el!, ".o_list_view");
    assert.containsN(webClient.el!, ".o_list_view .o_data_row", 5);

    await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient.el!, ".o_form_view");
    assert.hasClass(webClient.el!.querySelector(".o_form_view") as HTMLElement, "o_form_readonly");

    // go back using the breadcrumbs
    await testUtils.dom.click($(webClient.el!).find(".o_control_panel .breadcrumb-item a"));
    await legacyExtraNextTick();
    assert.containsOnce(webClient.el!, ".o_list_view");

    // create a new record
    await testUtils.dom.click($(webClient.el!).find(".o_list_button_add"));
    assert.containsOnce(webClient.el!, ".o_form_view");
    assert.hasClass(webClient.el!.querySelector(".o_form_view") as HTMLElement, "o_form_editable");

    webClient.destroy();
  });

  QUnit.test(
    "open form view, use the pager, execute action, and come back",
    async function (assert) {
      assert.expect(8);

      const webClient = await createWebClient({ testConfig });

      // execute an action and open a record
      await doAction(webClient, 3);
      assert.containsOnce(webClient.el!, ".o_list_view");
      assert.containsN(webClient.el!, ".o_list_view .o_data_row", 5);
      await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
      await legacyExtraNextTick();
      assert.containsOnce(webClient.el!, ".o_form_view");
      assert.strictEqual(
        $(webClient.el!).find(".o_field_widget[name=display_name]").text(),
        "First record"
      );

      // switch to second record
      await testUtils.dom.click($(webClient.el!).find(".o_pager_next"));
      assert.strictEqual(
        $(webClient.el!).find(".o_field_widget[name=display_name]").text(),
        "Second record"
      );

      // execute an action from the second record
      await testUtils.dom.click($(webClient.el!).find(".o_statusbar_buttons button[name=4]"));
      await legacyExtraNextTick();
      assert.containsOnce(webClient.el!, ".o_kanban_view");

      // go back using the breadcrumbs
      await testUtils.dom.click(
        $(webClient.el!).find(".o_control_panel .breadcrumb-item:nth(1) a")
      );
      await legacyExtraNextTick();
      assert.containsOnce(webClient.el!, ".o_form_view");
      assert.strictEqual(
        $(webClient.el!).find(".o_field_widget[name=display_name]").text(),
        "Second record"
      );

      webClient.destroy();
    }
  );

  QUnit.skip(
    "create a new record in a form view, execute action, and come back",
    async function (assert) {
      // need more work on list view (button create)
      assert.expect(8);

      const webClient = await createWebClient({ testConfig });

      // execute an action and create a new record
      await doAction(webClient, 3);
      assert.containsOnce(webClient.el!, ".o_list_view");
      await testUtils.dom.click($(webClient.el!).find(".o_list_button_add"));
      assert.containsOnce(webClient.el!, ".o_form_view");
      assert.hasClass($(webClient.el!).find(".o_form_view")[0], "o_form_editable");
      await testUtils.fields.editInput(
        $(webClient.el!).find(".o_field_widget[name=display_name]"),
        "another record"
      );
      await testUtils.dom.click($(webClient.el!).find(".o_form_button_save"));
      assert.hasClass($(webClient.el!).find(".o_form_view")[0], "o_form_readonly");

      // execute an action from the second record
      await testUtils.dom.click($(webClient.el!).find(".o_statusbar_buttons button[name=4]"));
      await legacyExtraNextTick();
      assert.containsOnce(webClient.el!, ".o_kanban_view");

      // go back using the breadcrumbs
      await testUtils.dom.click(
        $(webClient.el!).find(".o_control_panel .breadcrumb-item:nth(1) a")
      );
      await legacyExtraNextTick();
      assert.containsOnce(webClient.el!, ".o_form_view");
      assert.hasClass($(webClient.el!).find(".o_form_view")[0], "o_form_readonly");
      assert.strictEqual(
        $(webClient.el!).find(".o_field_widget[name=display_name]").text(),
        "another record"
      );

      webClient.destroy();
    }
  );

  QUnit.test("view with js_class attribute (legacy)", async function (assert) {
    assert.expect(2);
    const { AbstractView, legacyViewRegistry } = getLegacy() as any;

    const TestView = AbstractView.extend({
      viewType: "test_view",
    });
    legacyViewRegistry.add("test_view", TestView);

    const TestJsClassView = TestView.extend({
      init() {
        this._super.call(this, ...arguments);
        assert.step("init js class");
      },
    });
    legacyViewRegistry.add("test_jsClass", TestJsClassView);

    testConfig.serverData!.views!["partner,false,test_view"] = `
      <div js_class="test_jsClass"></div>
    `;
    testConfig.serverData!.actions![9999] = {
      id: 1,
      name: "Partners Action 1",
      res_model: "partner",
      type: "ir.actions.act_window",
      views: [[false, "test_view"]],
    };

    const webClient = await createWebClient({ testConfig });
    await doAction(webClient, 9999);
    assert.verifySteps(["init js class"]);
    delete legacyViewRegistry.map.test_view;
    delete legacyViewRegistry.map.test_jsClass;
    webClient.destroy();
  });

  QUnit.test(
    "on_close should be called only once with right parameters in js_class form view",
    async function (assert) {
      assert.expect(4);
      // This test is quite specific but matches a real case in legacy: event_configurator_widget.js
      // Clicking on form view's action button triggers its own mechanism: it saves the record and closes the dialog.
      // Now it is possible that the dialog action wants to do something of its own at closing time, to, for instance
      // update the main action behind it, with specific parameters.
      // This test ensures that this flow is supported in legacy,
      const { FormView, legacyViewRegistry } = (await getLegacy()) as any;

      const TestCustoFormController = FormView.prototype.config.Controller.extend({
        async saveRecord() {
          await this._super.apply(this, arguments);
          this.do_action({ type: "ir.actions.act_window_close", infos: { cantaloupe: "island" } });
        },
      });
      const TestCustoFormView = FormView.extend({});
      TestCustoFormView.prototype.config.Controller = TestCustoFormController;
      legacyViewRegistry.add("test_view", TestCustoFormView);

      testConfig.serverData!.views!["partner,1,form"] = `
      <form js_class="test_view">
        <field name="foo" />
        <footer>
          <button string="Echoes" special="save" />
        </footer>
      </form>`;

      const webClient = await createWebClient({ testConfig });
      await doAction(webClient, 24); // main form view
      await doAction(webClient, 25, {
        // Custom jsClass form view in target new
        onClose(infos: any) {
          assert.step("onClose");
          assert.deepEqual(infos, { cantaloupe: "island" });
        },
      });

      // Close dialog by clicking on save button
      await testUtils.dom.click(
        webClient.el!.querySelector(".o_dialog .modal-footer button[special=save]")
      );
      assert.verifySteps(["onClose"]);

      await legacyExtraNextTick();
      assert.containsNone(webClient.el!, ".modal");
      webClient.destroy();
      delete legacyViewRegistry.map.test_view;
    }
  );

  QUnit.test(
    "execute action without modal closes bootstrap tooltips anyway",
    async function (assert) {
      assert.expect(12);

      Object.assign(testConfig.serverData!.views!, {
        "partner,666,form": `<form>
            <header>
              <button name="object" string="Call method" type="object" help="need somebody"/>
            </header>
            <field name="display_name"/>
          </form>`,
      });

      const mockRPC: RPC = async (route, args) => {
        assert.step(route);
        if (route === "/web/dataset/call_button") {
          // Some business stuff server side, then return an implicit close action
          return Promise.resolve(false);
        }
      };
      const webClient = await createWebClient({ testConfig, mockRPC });
      await doAction(webClient, 24);
      assert.verifySteps([
        "/wowl/load_menus",
        "/web/action/load",
        "/web/dataset/call_kw/partner/load_views",
        "/web/dataset/call_kw/partner/read",
      ]);
      assert.containsN(webClient.el!, ".o_form_buttons_view button:not([disabled])", 2);
      const actionButton = webClient.el!.querySelector("button[name=object]");
      const tooltipProm = new Promise<void>((resolve) => {
        $(document.body).one("shown.bs.tooltip", () => {
          $(actionButton!).mouseleave();
          resolve();
        });
      });
      $(actionButton!).mouseenter();
      await tooltipProm;
      assert.containsN(document.body, ".tooltip", 2);
      await click(<HTMLElement>actionButton!);
      await legacyExtraNextTick();
      assert.verifySteps(["/web/dataset/call_button", "/web/dataset/call_kw/partner/read"]);
      assert.containsNone(document.body, ".tooltip"); // body different from webClient in tests !
      assert.containsN(webClient.el!, ".o_form_buttons_view button:not([disabled])", 2);
      webClient.destroy();
    }
  );

  QUnit.test("search view should keep focus during do_search", async function (assert) {
    assert.expect(5);

    // One should be able to type something in the search view, press on enter to
    // make the facet and trigger the search, then do this process
    // over and over again seamlessly.
    // Verifying the input's value is a lot trickier than verifying the search_read
    // because of how native events are handled in tests

    const searchPromise = testUtils.makeTestPromise();

    const mockRPC: RPC = async (route, args) => {
      if (route === "/web/dataset/call_kw/partner/web_search_read") {
        const { domain } = args!.kwargs;
        assert.step("search_read " + domain);
        if (JSON.stringify(domain) === JSON.stringify([["foo", "ilike", "m"]])) {
          await searchPromise;
        }
      }
    };
    const webClient = await createWebClient({ testConfig, mockRPC });
    await doAction(webClient, 3);

    await cpHelpers.editSearch(webClient.el!, "m");
    await cpHelpers.validateSearch(webClient.el!);

    assert.verifySteps(["search_read ", "search_read foo,ilike,m"]);

    // Triggering the do_search above will kill the current searchview Input
    await cpHelpers.editSearch(webClient.el!, "o");

    // We have something in the input of the search view. Making the search_read
    // return at this point will trigger the redraw of the view.
    // However we want to hold on to what we just typed
    searchPromise.resolve();
    await cpHelpers.validateSearch(webClient.el!);

    assert.verifySteps(["search_read |,foo,ilike,m,foo,ilike,o"]);

    webClient.destroy();
  });

  QUnit.test(
    "Call twice clearUncommittedChanges in a row does not display twice the discard warning",
    async function (assert) {
      assert.expect(4);

      const webClient = await createWebClient({ testConfig });

      // execute an action and edit existing record
      await doAction(webClient, 3);

      await testUtils.dom.click($(webClient.el!).find(".o_list_view .o_data_row:first"));
      await legacyExtraNextTick();
      assert.containsOnce(webClient, ".o_form_view.o_form_readonly");

      await testUtils.dom.click($(webClient.el!).find(".o_control_panel .o_form_button_edit"));
      assert.containsOnce(webClient, ".o_form_view.o_form_editable");

      await testUtils.fields.editInput($(webClient.el!).find("input[name=foo]"), "val");
      clearUncommittedChanges(webClient.env);
      await testUtils.nextTick();
      await legacyExtraNextTick();

      assert.containsOnce(document.body, ".modal"); // confirm discard dialog
      // confirm discard changes
      await testUtils.dom.click($(".modal .modal-footer .btn-primary"));

      clearUncommittedChanges(webClient.env);
      await testUtils.nextTick();
      await legacyExtraNextTick();

      assert.containsNone(document.body, ".modal");

      webClient.destroy();
    }
  );
});
