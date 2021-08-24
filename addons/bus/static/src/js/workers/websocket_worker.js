/** @odoo-module **/

/**
 * Possible type for the messages sent from the worker to the websocket_service
 *
 * @typedef {'connect' | 'reconnect' | 'disconnect' | 'reconnecting' | 'server_error' | 'notification'} MessageType
 */

/**
 * This class regroups the logic necessary in order for the SharedWorker/Worker to work.
 * Indeed, Safari and some minor browsers does not support SharedWorker. In order to
 * solve this issue, a Worker is used in this case. The logic is almost the same than
 * the one used for SharedWorker and this class implements it.
 */
class WebsocketWorker {
    constructor(websocketURL, websocketClass = WebSocket, setTimeoutFn = setTimeout) {
        this.websocketURL = websocketURL;
        this.websocketClass = websocketClass;
        this.connectRetryDelay = 1000;
        this.connectTimeout = null;
        this.messageWaitQueue = [];
        this.clientUIDToClient = {};
        this.onWebsocketOpen = this.onWebsocketOpen.bind(this);
        this.onWebsocketClose = this.onWebsocketClose.bind(this);
        this.onWebsocketError = this.onWebsocketError.bind(this);
        this.onWebsocketMessage = this.onWebsocketMessage.bind(this);
        this.setTimeout = (fn, timeout) => setTimeoutFn(fn, timeout);
        this.start();
    }

    /**
     * Start the worker by opening a websocket connection
     */
    start() {
        this.websocket = new this.websocketClass(this.websocketURL);
        this.websocket.addEventListener('open', this.onWebsocketOpen);
        this.websocket.addEventListener('error', this.onWebsocketError);
        this.websocket.addEventListener('message', this.onWebsocketMessage);
        this.websocket.addEventListener('close', this.onWebsocketClose);
    }

    /**
     * Register a client handled by this worker. Each client is given an UID.
     *
     * @param {MessagePort} messagePort
     */
    registerClient(messagePort) {
        const clientUID = Date.now().toString(36) + Math.random().toString(36).substr(2);
        this.clientUIDToClient[clientUID] = messagePort;
        messagePort.onmessage = messageEv => {
            const { action, data = {} } = messageEv.data;
            data['client_uid'] = clientUID;
            this.onMessage({ action, data });
        };
    }

    /**
     * Called when a message is posted to the worker
     *
     * @param {Object} message
     * @param {'send' | 'reconnect' | 'leave'} message.action Action to execute
     * @param {*} message.data Optional data required by the action
     */
    onMessage(message) {
        const { action, data } = message;
        if (action === 'send') {
            const message = JSON.stringify(data);
            if (!this.websocket || this.websocket.readyState !== 1) {
                this.messageWaitQueue.push(message);
            } else {
                this.websocket.send(message);
            }
        } else if (action === 'reconnect') {
            this.isReconnecting = true;
            this.websocket.close(1000);
        } else if (action === 'leave') {
            const { client_uid } = data;
            delete this.clientUIDToClient[client_uid];
        }
    }

    /**
    * Handle data receive from the bus. If it's an array, it's notifications if not,
    * it's an error. Trigger the appropriate event.
    *
    * @param {MessageEvent} messageEv
    */
    onWebsocketMessage(messageEv) {
        const data = JSON.parse(messageEv.data);
        if (!Array.isArray(data)) {
            this.sendToClient(data['client_uid'], 'server_error', data);
        } else {
            this.broadcast('notification', data.map(notification => notification.message));
        }
    }

    /**
     * Triggered when a connection was established then closed. If closure was not clean (ie. code
     * !== 1000), try to reconnect after indicating to the clients that the connection was closed.
     *
     * @param {CloseEvent} ev
     */
    onWebsocketClose(ev) {
        if (this.isReconnecting) {
            this.start();
        } else {
            this.broadcast('disconnect', {code: ev.code, reason: ev.reason});
            if (ev.code !== 1000) {
                this.onWebsocketError();
            }
        }
    }

    /**
     * Triggered when a connection failed or failed to established. Apply an exponential
     * back off to the reconnect attempts.
     */
    onWebsocketError() {
        this.removeWebsocketListeners();
        this.connectRetryDelay = this.connectRetryDelay * 1.5 + 500 * Math.random();
        this.connectTimeout = this.setTimeout(this.start.bind(this), this.connectRetryDelay);
        this.broadcast('reconnecting');
    }

    /**
     * Triggered on websocket open. Send message that were waiting for the connection
     * to open.
     */
    onWebsocketOpen() {
        this.messageWaitQueue.forEach(msg => this.websocket.send(msg));
        this.messageWaitQueue = [];
        if (!this.isReconnecting) {
            this.broadcast(this.connectTimeout ? 'reconnect' : 'connect');
        }
        this.isReconnecting = false;
        this.connectRetryDelay = 1000;
        this.connectTimeout = null;
    }

    removeWebsocketListeners() {
        if (this.websocket) {
            this.websocket.removeEventListener('message', this.onWebsocketMessage);
            this.websocket.removeEventListener('close', this.onWebsocketClose);
            this.websocket.removeEventListener('error', this.onWebsocketError);
        }
    }

    /**
     * Send the message to all the clients that are connected to the worker.
     *
     * @param {MessageType} type
     * @param {*} data
     */
    broadcast(type, data) {
        Object.values(this.clientUIDToClient)
            .forEach(client => client.postMessage({type, data}));
    }

    /**
     * Send message to the client matching the given clientUID
     *
     * @param {number} clientUID
     * @param {MessageType} type
     * @param {*} data
     */
    sendToClient(clientUID, type, data) {
        if (clientUID in this.clientUIDToClient) {
            this.clientUIDToClient[clientUID].postMessage({type, data});
        }
    }

}

// This class is used by the workers (importScript) and by the WebsocketMockWorker class.
// The issue is that one is in an es6 module context while the other is not.
// This means that one need to import this class (which means this class should be exported)
// and the other does not support the es6 module syntax (so export would lead to SyntaxError).
// In order to avoid this problem, this class is added to the global window object if it is defined
// allowing the WebsocketMockWorker class to retrieve it and the workers to import the script
// without syntax error.
if (typeof window !== 'undefined' && window !== null) {
    window.WebsocketWorker = WebsocketWorker;
}
