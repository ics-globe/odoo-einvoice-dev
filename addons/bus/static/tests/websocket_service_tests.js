/** @odoo-module */

import { websocketService } from "@bus/js/services/websocket_service";
import { patchWebsocketWithCleanup } from "@web/../tests/helpers/mock_websocket";
import { nextTick } from "@web/../tests/helpers/utils";
import { createWebClient } from "@web/../tests/webclient/helpers";
import { registry } from "@web/core/registry";

QUnit.module("Websocket Service", () => {
    QUnit.test("websocket service displays reconnect notification according to worker events", async (assert) => {
        assert.expect(3);

        const { worker } = patchWebsocketWithCleanup();
        registry.category("services").add('websocketService', websocketService);

        await createWebClient({});
        worker.broadcast('reconnecting');
        await nextTick();

        assert.containsOnce(document.body, '.o_notification');
        assert.strictEqual(
            document.querySelector('.o_notification .o_notification_content').textContent,
            'Websocket connection lost. Trying to reconnect...'
        );

        worker.broadcast('reconnect');
        await nextTick();

        assert.containsNone(document.body, '.o_notification');
    });
});
