/** @odoo-module */

import { createWebClient } from "@web/../tests/webclient/helpers";
import { assetsWatchdogService } from "@bus/js/services/assets_watchdog_service";
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { busService } from '@bus/js/services/bus_service';
import { websocketService } from '@bus/js/services/websocket_service';
import { patchWebsocketWithCleanup } from "@web/../tests/helpers/mock_websocket";

const serviceRegistry = registry.category("services");

QUnit.module("Bus Assets WatchDog", (hooks) => {
    let target;
    hooks.beforeEach((assert) => {
        serviceRegistry.add("bus_service", busService);
        serviceRegistry.add("websocketService", websocketService);
        serviceRegistry.add("assetsWatchdog", assetsWatchdogService);
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
            location: {
                reload: () => assert.step("reloadPage"),
            },
        });

        target = getFixture();
    });

    QUnit.test("can listen on bus and displays notifications in DOM", async (assert) => {
        assert.expect(4);

        const bundleChangedNotification = [{
            message: {
                type: 'bundle_changed',
                payload: { server_version: "NEW_MAJOR_VERSION" },
            },
        }];

        // trigger a message event containing the bundle changed notification
        // once the websocket bus is started.
        patchWebsocketWithCleanup({
            send: function (message) {
                const { path } = JSON.parse(message);
                if (path === '/subscribe') {
                    this.dispatchEvent(new MessageEvent('message', {
                        data: JSON.stringify(bundleChangedNotification),
                    }));
                }
            },
        });

        await createWebClient({});

        assert.containsOnce(target, ".o_notification_body");
        assert.strictEqual(
            target.querySelector(".o_notification_body .o_notification_content").textContent,
            "The page appears to be out of date."
        );

        // reload by clicking on the reload button
        await click(target, ".o_notification_buttons .btn-primary");
        assert.verifySteps(["reloadPage"]);
    });
});
