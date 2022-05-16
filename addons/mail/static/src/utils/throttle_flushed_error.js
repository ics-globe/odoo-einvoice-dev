/** @odoo-module **/

/**
 * Error when throttle function has been flushed with `.flush()`. Used
 * internally to immediately invoke pending inner functions, since a flush means
 * the termination of cooling down phase.
 *
 * @private
 */
export class ThrottleFlushedError extends Error {
    /**
     * @override
     */
    constructor(throttleId, ...args) {
        super(...args);
        this.name = '_ThrottleFlushedError';
        this.throttleId = throttleId;
    }
}
