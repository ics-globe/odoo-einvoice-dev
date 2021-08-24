/** @odoo-module */

import { patchWebsocketWorkerWithCleanup } from "@web/../tests/helpers/mock_websocket";
import { patchWithCleanup, nextTick } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";

QUnit.module("Websocket Worker", (hooks) => {
    hooks.beforeEach(() => {
        patchWithCleanup(browser, {
            setTimeout: fn => {
                fn();
                return 1;
            }
        });
    });

    QUnit.test('connection event is broadcasted', async function (assert) {
        patchWebsocketWorkerWithCleanup({
            mockWebsocket: {
                onopen: () => {
                    assert.step('websocket connected');
                },
            },
            mockWebsocketWorker: {
                broadcast: type => {
                    assert.step(`broadcast ${type}`);
                },
            },
        });
        await nextTick();

        assert.verifySteps([
            'websocket connected',
            'broadcast connect',
        ]);
    });

    QUnit.test('disconnection event is broadcasted', async function (assert) {
        const { worker } = patchWebsocketWorkerWithCleanup({
            mockWebsocket: {
                onclose: () => {
                    assert.step('websocket disconnected');
                }
            },
            mockWebsocketWorker: {
                broadcast: type => {
                    assert.step(`broadcast ${type}`);
                },
            },
        });

        // wait for the websocket to connect
        await nextTick();
        worker.websocket.close(1000);

        assert.verifySteps([
            'broadcast connect',
            'websocket disconnected',
            'broadcast disconnect',
        ]);
    });

    QUnit.test('leave action updates client map', async (assert) => {
        assert.expect(2);

        const { worker, client } = patchWebsocketWorkerWithCleanup();
        assert.strictEqual(1, Object.keys(worker.clientUIDToClient).length);

        client.onmessage(new MessageEvent('message', {
            data: { action: 'leave' },
        }));
        assert.strictEqual(0, Object.keys(worker.clientUIDToClient).length);
    });

    QUnit.test('abnormal closure leads to reconnect', async function (assert) {
        const { worker } = patchWebsocketWorkerWithCleanup({
            mockWebsocket: {
                onopen: () => {
                    assert.step('websocket connected');
                },
                onclose: () => {
                    assert.step('websocket disconnected');
                }
            },
            mockWebsocketWorker: {
                broadcast: type => {
                    assert.step(`broadcast ${type}`);
                },
            },
        });

        // wait for the websocket to connect
        await nextTick();
        worker.websocket.close(1006);
        // wait for the connection to be closed properly
        await nextTick();

        assert.verifySteps([
            'websocket connected',
            'broadcast connect',
            'websocket disconnected',
            'broadcast disconnect',
            'broadcast reconnecting',
            'websocket connected',
            'broadcast reconnect',
        ]);
    });

    QUnit.test("error is relayed to the client that caused it", function (assert) {
        assert.expect(2);

        let firstClientUID;
        const { worker } = patchWebsocketWorkerWithCleanup({
            mockWebsocketWorker: {
                sendToClient: (clientUID, type) => {
                    assert.strictEqual(type, 'server_error');
                    assert.strictEqual(clientUID, firstClientUID);
                },
            },
        });
        worker.registerClient({ postMessage() {} });
        worker.registerClient({ postMessage() {} });

        firstClientUID = Object.keys(worker.clientUIDToClient)[0];
        worker.websocket.dispatchEvent(new MessageEvent('message', {
            data: JSON.stringify({
                name: 'odoo.exceptions.AccessDenied',
                debug: '...',
                client_uid: firstClientUID,
            }),
        }));
    });
});
