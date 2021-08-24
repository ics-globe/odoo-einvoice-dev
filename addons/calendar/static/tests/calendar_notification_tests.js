/** @odoo-module */

import { createWebClient } from "@web/../tests/webclient/helpers";
import { calendarNotificationService } from "@calendar/js/services/calendar_notification_service";
import { click, getFixture, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { busService } from "@bus/js/services/bus_service";
import { websocketService } from "@bus/js/services/websocket_service";
import { patchWebsocketWithCleanup } from "@web/../tests/helpers/mock_websocket";

const serviceRegistry = registry.category("services");
let target;
QUnit.module("Calendar Notification", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serviceRegistry.add("bus_service", busService);
        serviceRegistry.add("websocketService", websocketService);
        serviceRegistry.add("calendarNotification", calendarNotificationService);

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });

        const calendarAlarmNotification = [{
            message: {
                type: "calendar.alarm",
                payload: [{
                    alarm_id: 1,
                    event_id: 2,
                    title: "Meeting",
                    message: "Very old meeting message",
                    timer: 20 * 60,
                    notify_at: "1978-04-14 12:45:00",
                }],
            }
        }];

        // trigger a message event containing the calendar alarm notification
        // once the websocket bus is started.
        patchWebsocketWithCleanup({
            send: function (message) {
                const { path } = JSON.parse(message);
                if (path === '/subscribe') {
                    this.dispatchEvent(new MessageEvent('message', {
                        data: JSON.stringify(calendarAlarmNotification),
                    }));
                }
            }
        });
    });

    QUnit.test(
        "can listen on bus and display notifications in DOM and click OK",
        async (assert) => {
            assert.expect(5);

            const mockRPC = (route, args) => {
                if (route === "/calendar/notify") {
                    return Promise.resolve([]);
                }
                if (route === "/calendar/notify_ack") {
                    assert.step("notifyAck");
                    return Promise.resolve(true);
                }
            };

            await createWebClient({ mockRPC });

            await nextTick();

            assert.containsOnce(target, ".o_notification_body");
            assert.strictEqual(
                target.querySelector(".o_notification_body .o_notification_content")
                    .textContent,
                "Very old meeting message"
            );

            await click(target.querySelector(".o_notification_buttons .btn"));
            assert.verifySteps(["notifyAck"]);
            assert.containsNone(target, ".o_notification");
        }
    );

    QUnit.test(
        "can listen on bus and display notifications in DOM and click Detail",
        async (assert) => {
            assert.expect(5);

            const mockRPC = (route, args) => {
                if (route === "/calendar/notify") {
                    return Promise.resolve([]);
                }
            };

            const fakeActionService = {
                name: "action",
                start() {
                    return {
                        doAction(actionId) {
                            assert.step(actionId.type);
                            return Promise.resolve(true);
                        },
                        loadState(state, options) {
                            return Promise.resolve(true);
                        },
                    };
                },
            };
            serviceRegistry.add("action", fakeActionService, { force: true });

            await createWebClient({ mockRPC });

            await nextTick();

            assert.containsOnce(target, ".o_notification_body");
            assert.strictEqual(
                target.querySelector(".o_notification_body .o_notification_content")
                    .textContent,
                "Very old meeting message"
            );

            await click(target.querySelectorAll(".o_notification_buttons .btn")[1]);
            assert.verifySteps(["ir.actions.act_window"]);
            assert.containsNone(target, ".o_notification");
        }
    );

    QUnit.test(
        "can listen on bus and display notifications in DOM and click Snooze",
        async (assert) => {
            assert.expect(4);

            const mockRPC = (route, args) => {
                if (route === "/calendar/notify") {
                    return Promise.resolve([]);
                }
                if (route === "/calendar/notify_ack") {
                    assert.step("notifyAck");
                    return Promise.resolve(true);
                }
            };

            await createWebClient({ mockRPC });

            await nextTick();

            assert.containsOnce(target, ".o_notification_body");
            assert.strictEqual(
                target.querySelector(".o_notification_body .o_notification_content")
                    .textContent,
                "Very old meeting message"
            );

            await click(target.querySelectorAll(".o_notification_buttons .btn")[2]);
            assert.verifySteps([], "should only close the notification withtout calling a rpc");
            assert.containsNone(target, ".o_notification");
        }
    );
});
