/** @odoo-module **/

/**
 * Error when throttle function has been canceled with `.cancel()`. Used to
 * let the caller know of throttle function that the call has been canceled,
 * which means the inner function will not be called. Usually caller should
 * just accept it and kindly treat this error as a polite warning.
 */
export class ThrottleCanceledError extends Error {
    /**
     * @override
     */
    constructor(throttleId, ...args) {
        super(...args);
        this.name = 'ThrottleCanceledError';
        this.throttleId = throttleId;
    }
}
