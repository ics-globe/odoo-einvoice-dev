/** @odoo-module **/

/**
 * Error when throttle function has been reinvoked again. Used to let know
 * caller of throttle function that the call has been canceled and replaced with
 * another one, which means the (potentially) following inner function will be
 * in the context of another call. Same as for `ThrottleCanceledError`, usually
 * caller should just accept it and kindly treat this error as a polite
 * warning.
 */
export class ThrottleReinvokedError extends Error {
    /**
     * @override
     */
    constructor(throttleId, ...args) {
        super(...args);
        this.name = 'ThrottleReinvokedError';
        this.throttleId = throttleId;
    }
}
