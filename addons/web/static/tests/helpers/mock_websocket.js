/** @odoo-module **/
import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

export class WebsocketMock extends EventTarget {
    constructor(url, options) {
        super();
        this.readyState = 0;
        this.url = url;
        options = options || {};
        this.onopen = options.onopen || null;
        this.onclose = options.onclose || null;
        this.onmessage = options.onmessage || null;
        this.onerror = options.onerror || null;
        if (options.send) {
            this.send = (data) => {
                this._send(data);
                options.send.call(this, data);
            };
        }
        if (options.close) {
            this.close = (ev) => {
                this._close(ev);
                options.close.call(this, ev);
            };
        }
        queueMicrotask(() => {
            this.readyState = 1;
            const openEv = new Event('open');
            if (this.onopen) {
                this.onopen(openEv);
            }
            this.dispatchEvent(openEv);
        });
    }

    send(data) {
        this._send(data);
    }

    close(code, reason) {
        this._close(code, reason);
    }

    _close(code, reason) {
        this.readyState = 3;
        const closeEv = new CloseEvent('close', {
            code,
            reason,
            wasClean: code === 1000,
        });
        if (this.onclose) {
            this.onclose(closeEv);
        }
        this.dispatchEvent(closeEv);
    }

    _send() {
        if (this.readyState !== 1) {
            const errorEv = new Event('error');
            this.dispatchEvent(errorEv);
            if (this.onerror) {
                this.onerror(errorEv);
            }
            throw new DOMException("Failed to execute 'send' on 'WebSocket': State is not OPEN");
        }
    }
}

export class WebsocketWorkerMock extends EventTarget {
    constructor(scriptURL, options) {
        super();
        this.worker = new window.WebsocketWorker(
            'wss://random-url.com/websocket',
            function (url) {
                return new WebsocketMock(url, options || {});
            },
            browser.setTimeout,
        );
        this.client = {
            postMessage: message => {
                this.dispatchEvent(new MessageEvent('message', {
                    data: message,
                }));
            },
            onmessage: () => {},
        };
        this.worker.registerClient(this.client);
    }

    /**
     * @param {*} message
     */
    postMessage(message) {
        this.client.onmessage(new MessageEvent('message', {
            data: message,
        }));
    }
}

export class WebsocketSharedWorkerMock extends WebsocketWorkerMock {
    constructor(scriptURL, options) {
        super(scriptURL, options);
        this.port = {
            postMessage: this.postMessage.bind(this),
            addEventListener: this.addEventListener.bind(this),
            removeEventListener: this.removeEventListener.bind(this),
            start: () => {},
        };
    }
}

export function patchWebsocketWorkerWithCleanup(options = {}) {
    patchWithCleanup(window.WebsocketWorker.prototype, options.mockWebsocketWorker || {});
    const worker = patchWebsocketWithCleanup(options.mockWebsocket);
    return worker;
}

export function patchWebsocketWithCleanup(options = {}) {
    let worker;
    const patch = {};
    if ('SharedWorker' in window) {
        worker = new WebsocketSharedWorkerMock('worker_script.js', options);
        patch['SharedWorker'] = function() {
            return worker;
        }
    } else {
        worker = new WebsocketWorkerMock('worker_script.js', options);
        patch['Worker'] = function() {
            return worker;
        }
    }
    patchWithCleanup(browser, patch, { pure: true });
    return worker;
}
