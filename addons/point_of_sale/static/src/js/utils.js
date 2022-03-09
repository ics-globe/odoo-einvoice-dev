odoo.define('point_of_sale.utils', function (require) {
    'use strict';

    const { ConnectionAbortedError, ConnectionLostError } = require('@web/core/network/rpc_service');

    function getFileAsText(file) {
        return new Promise((resolve, reject) => {
            if (!file) {
                reject();
            } else {
                const reader = new FileReader();
                reader.addEventListener('load', function () {
                    resolve(reader.result);
                });
                reader.addEventListener('abort', reject);
                reader.addEventListener('error', reject);
                reader.readAsText(file);
            }
        });
    }

    /**
     * This global variable is used by nextFrame to store the timer and
     * be able to cancel it before another request for animation frame.
     */
    let timer = null;

    /**
     * Wait for the next animation frame to finish.
     */
    const nextFrame = () => {
        return new Promise((resolve) => {
            cancelAnimationFrame(timer);
            timer = requestAnimationFrame(() => {
                resolve();
            });
        });
    };

    function isConnectionError(error) {
        return error instanceof ConnectionAbortedError || error instanceof ConnectionLostError;
    }

    /**
     * Creates a batched version of a callback so that all calls to it in the same
     * microtick will only call the original callback once.
     *
     * @param callback the callback to batch
     * @returns a batched version of the original callback
     */
    function batched(callback) {
        let called = false;
        return async () => {
            // This await blocks all calls to the callback here, then releases them sequentially
            // in the next microtick. This line decides the granularity of the batch.
            await Promise.resolve();
            if (!called) {
                called = true;
                callback();
                // wait for all calls in this microtick to fall through before resetting "called"
                // so that only the first call to the batched function calls the original callback
                await Promise.resolve();
                called = false;
            }
        };
    }

    return { getFileAsText, nextFrame, isConnectionError, batched };
});
