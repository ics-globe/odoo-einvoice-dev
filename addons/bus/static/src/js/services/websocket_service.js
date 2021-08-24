/** @odoo-module **/
import { browser } from "@web/core/browser/browser";
import { registry } from '@web/core/registry';
import { WebsocketError } from '@bus/js/websocket_errors';

const { EventBus } = owl;
/**
 * Communicate with a SharedWorker in order to provide a single websocket
 * connection shared across multiple tabs.
 *
 *  @emits connect
 *  @emits disconnect
 *  @emits reconnect
 *  @emits reconnecting
 *  @emits server_error
 *  @emits notification
 */
export const websocketService = {
    dependencies: ['notification', 'user'],
    _removeConnectionLostNotification: null,

    start(env) {
        this.env = env;
        this._bus = new EventBus();
        this._usesSharedWorker = true;
        if ('SharedWorker' in window) {
            this.worker = new browser.SharedWorker(
                '/bus/static/src/js/workers/websocket_shared_worker.js',
                { name: "odoo:websocket_shared_worker" });
            this.worker.port.start();
            this.worker.port.addEventListener('message', this._handleMessage.bind(this));
        } else {
            // Fallback for browsers which does not support SharedWorker.
            this.worker = new browser.Worker(
                '/bus/static/src/js/workers/websocket_simple_worker.js',
                { name: "odoo:websocket_worker" });
            this.worker.addEventListener('message', this._handleMessage.bind(this));
            this._usesSharedWorker = false;
        }
        const { userId } = this.env.services.user;
        if (sessionStorage.getItem('websocket_should_reconnect') && userId) {
            // A SessionExpiredException was received and the page was reload. Since the
            // auth cookie is passed to the websocket during the http handshake, refresh
            // the connection hence the cookie.
            sessionStorage.removeItem('websocket_should_reconnect');
            this._send('reconnect');
        }
        window.addEventListener('beforeunload', () => this._send('leave'));
        return {
            send: this.send.bind(this),
            on: this._bus.on.bind(this._bus),
            off: this._bus.off.bind(this._bus),
        };
    },

   //--------------------------------------------------------------------------
   // PUBLIC
   //--------------------------------------------------------------------------

    /**
     * Send a message through the websocket.
     *
     * @param {{path: string, kwargs: Object}} message
     */
    send(message) {
        this._send('send', message);
    },

   //--------------------------------------------------------------------------
   // PRIVATE
   //--------------------------------------------------------------------------

    /**
    * Send a message to the worker
    *
    * @param {'send' | 'reconnect' | 'leave'} action Action to be executed by the worker
    * @param {*} data Optional data required for the action to be executed
    */
    _send(action, data) {
        const message = { action, data };
        if (this._usesSharedWorker) {
            this.worker.port.postMessage(message);
        } else {
            this.worker.postMessage(message);
        }
    },
    /**
     * Handle messages received from the shared worker and fires an event
     * according to the message type.
     *
     * @param {MessageEvent} messageEv
     * @param {{type: MessageType, data: any}[]}  messageEv.data
     */
    _handleMessage(messageEv) {
        const {type, data} = messageEv.data;
        if (type === 'reconnecting') {
            if (!this._removeConnectionLostNotification) {
                this._removeConnectionLostNotification = this.env.services.notification.add(
                    this.env._t("Websocket connection lost. Trying to reconnect..."),
                    { sticky: true },
                );
            }
        } else if (type === 'reconnect') {
            this._removeConnectionLostNotification();
            this._removeConnectionLostNotification = null;
        } else if (type === 'server_error') {
            this._handleServerError(data);
        }
        this._bus.trigger(type, data);
    },
    /**
     * Called upon the reception of a server error. If the error is a SessionExpiredException
     * and we're using a SharedWorker, use session storage in order to refresh the websocket
     * connection after reload. There is no need to do this with a simple WebWorker because
     * refreshing the page will re-create the worker thus restarting the WebSocket.
     *
     * @param {Object} error
     */
    _handleServerError(error) {
        if (error.name === 'odoo.http.SessionExpiredException' && this._usesSharedWorker) {
            sessionStorage.setItem('websocket_should_reconnect', true);
        }
        // reject promise instead of throwing in order to trigger the error without
        // interrupting the flow (we want the bus to trigger the event anyway).
        new Promise((res, rej) => rej(new WebsocketError(error)));
    }
};

registry.category('services').add('websocketService', websocketService);
