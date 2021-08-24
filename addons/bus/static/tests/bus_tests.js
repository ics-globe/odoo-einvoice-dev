/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { busService } from '@bus/js/services/bus_service';
import { createWebClient } from "@web/../tests/webclient/helpers";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { patchWebsocketWithCleanup } from '@web/../tests/helpers/mock_websocket';
import { patchWithCleanup, nextTick } from '@web/../tests/helpers/utils';
import { registry } from '@web/core/registry';
import { websocketService } from '@bus/js/services/websocket_service';

const serviceRegistry = registry.category("services");

QUnit.module('Bus', function (hooks) {
    hooks.beforeEach(() => {
        patchWithCleanup(browser, {
            setTimeout: fn => {
                fn();
                return 1;
            },
        });
        serviceRegistry.add('websocketService', websocketService);
        serviceRegistry.add('bus_service', busService);
    });

    QUnit.test('notifications received from websocket after channel subscription',
    async function (assert) {
        assert.expect(4);

        const notifications = [
            [{
                message: 'beta',
            }], [{
                message: 'epsilon',
            }],
        ];

        patchWebsocketWithCleanup({
            send: function (message) {
                const { path, kwargs } = JSON.parse(message);
                if (path === '/subscribe') {
                    assert.step(path + ' - ' + kwargs.channels.join(','));
                    notifications.forEach(notif => {
                        this.dispatchEvent(new MessageEvent('message', {
                            data: JSON.stringify(notif),
                        }));
                    });
                }
            },
        });

        const env = await makeTestEnv();
        env.services.bus_service.onNotification(this, function (notifications) {
            assert.step('notification - ' + notifications.toString());
        });
        env.services.bus_service.addChannel('lambda');

        await nextTick();

        assert.verifySteps([
            '/subscribe - lambda',
            'notification - beta',
            'notification - epsilon',
        ]);
    });

    QUnit.test('WebSocket reconnects/resubscribe after connection is lost',
    async function (assert) {
        assert.expect(4);

        let connectionCount = 0;
        patchWebsocketWithCleanup({
            send: function (message) {
                const { path } = JSON.parse(message);
                if (path === '/subscribe') {
                    assert.step(`websocket connected ${connectionCount++}`);
                    if (connectionCount === 1) {
                        // 1006 means the connection has been closed unexpectedly
                        // Thus, the bus should try to reconnect.
                        this.close(1006);
                    } else {
                        assert.equal(connectionCount, 2, "shouldn't be called after clean closure");
                        // 1000 means the connection has been closed cleanly
                        // Thus, the bus should not try to reconnect.
                        this.close(1000);
                    }
                }
            },
        });

        const { env } = await createWebClient({});
        env.services.bus_service.startBus();

        // Give websocket a tick to reconnect
        await nextTick();

        assert.verifySteps([
            'websocket connected 0',
            'websocket connected 1',
        ]);
    });
});
