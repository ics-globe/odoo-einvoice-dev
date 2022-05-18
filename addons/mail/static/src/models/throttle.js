/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';
import { makeDeferred } from '@mail/utils/deferred';
import { ThrottleCanceledError } from '@mail/utils/throttle_canceled_error';
import { ThrottleFlushedError } from '@mail/utils/throttle_flushed_error';
import { ThrottleReinvokedError } from '@mail/utils/throttle_reinvoked_error';

/**
 * This module define an utility function that enables throttling calls on a
 * provided function. Such throttled calls can be canceled, flushed and/or
 * cleared:
 *
 * - cancel: Canceling a throttle function call means that if a function call is
 *   pending invocation, cancel removes this pending call invocation. It however
 *   preserves the internal timer of the cooling down phase of this throttle
 *   function, meaning that any following throttle function call will be pending
 *   and has to wait for the remaining time of the cooling down phase before
 *   being invoked.
 *
 * - flush: Flushing a throttle function call means that if a function call is
 *   pending invocation, flush immediately terminates the cooling down phase and
 *   the pending function call is immediately invoked. Flush also works without
 *   any pending function call: it just terminates the cooling down phase, so
 *   that a following function call is guaranteed to be immediately called.
 *
 * - clear: Clearing a throttle function combines canceling and flushing
 *   together.
 */
registerModel({
    name: 'Throttle',
    identifyingFields: [[
        'threadAsThrottleNotifyCurrentPartnerTypingStatus',
    ]],
    recordMethods: {
        /**
         * Cancel any buffered function call while keeping the cooldown phase
         * running.
         */
        cancel() {
            if (!this.isCoolingDown) {
                return;
            }
            if (!this.pendingInvokeDeferred) {
                return;
            }
            this.pendingInvokeDeferred.reject(new ThrottleCanceledError(this.id));
        },
        /**
         * Clear any buffered function call and immediately terminates any cooling
         * down phase in progress.
         */
        clear() {
            this.cancel();
            this.flush();
        },
        /**
         * 
         * @param  {...any} args
         * @returns {any}
         */
        async do(...args) {
            try {
                // await is important, otherwise errors are not intercepted.
                return await this._do(...args);
            } catch (error) {
                const isSelfReinvokedError = (
                    error instanceof ThrottleReinvokedError &&
                    error.throttleId === this.id
                );
                const isSelfCanceledError = (
                    error instanceof ThrottleCanceledError &&
                    error.throttleId === this.id
                );
    
                if (this.hasSilentCancelationErrors && (isSelfReinvokedError || isSelfCanceledError)) {
                    // Silently ignore cancelation errors.
                    // Promise is indefinitely pending for async functions.
                    return new Promise(() => {});
                } else {
                    throw error;
                }
            }
        },
        /**
         * Flush the internal throttle timer, so that the following function call
         * is immediate. For instance, if there is a cooldown stage, it is aborted.
         */
        flush() {
            if (!this.isCoolingDown) {
                return;
            }
            const coolingDownDeferred = this.coolingDownDeferred;
            this.update({
                coolingDownDeferred: clear(),
                isCoolingDown: false,
            });
            coolingDownDeferred.reject(new ThrottleFlushedError(this.id));
        },
        /**
         * @private
         * @returns {integer|FieldCommand}
         */
        _computeDuration() {
            if (this.threadAsThrottleNotifyCurrentPartnerTypingStatus) {
                return 2.5 * 1000;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeId() {
            return _.uniqueId('throttle_');
        },
        /**
         * Called when there is a call to the function. This function is throttled,
         * so the time it is called depends on whether the "cooldown stage" occurs
         * or not:
         *
         * - no cooldown stage: function is called immediately, and it starts
         *      the cooldown stage when successful.
         * - in cooldown stage: function is called when the cooldown stage has
         *      ended from timeout.
         *
         * Note that after the cooldown stage, only the last attempted function
         * call will be considered.
         *
         * @private
         * @param {...any} args
         * @throws {ThrottleReinvokedError|ThrottleCanceledError}
         * @returns {any} result of called function, if it's called.
         */
        async _do(...args) {
            if (!this.isCoolingDown) {
                return this._invokeFunction(...args);
            }
            if (this.pendingInvokeDeferred) {
                this.pendingInvokeDeferred.reject(new ThrottleReinvokedError(this.id));
            }
            try {
                this.update({ pendingInvokeDeferred: makeDeferred() });
                await Promise.race([this.coolingDownDeferred, this.pendingInvokeDeferred]);
            } catch (error) {
                if (
                    !(error instanceof ThrottleFlushedError) ||
                    error.throttleId !== this.id
                ) {
                    throw error;
                }
            } finally {
                this.update({ pendingInvokeDeferred: clear() });
            }
            return this._invokeFunction(...args);
        },
        /**
         * Invoke the inner function of this throttle and starts cooling down phase
         * immediately after.
         *
         * @private
         * @param  {...any} args
         */
        async _invokeFunction(...args) {
            const res = this.func(...args);
            this._startCoolingDown();
            return res;
        },
        /**
         * Called just when the inner function is being called. Starts the cooling
         * down phase, which turn any call to this throttle function as pending
         * inner function calls. This will be called after the end of cooling down
         * phase (except if canceled).
         */
        async _startCoolingDown() {
            if (this.coolingDownDeferred) {
                throw new Error("Cannot start cooling down if there's already a cooling down in progress.");
            }
            this.update({
                cooldownTimer: insertAndReplace(),
                coolingDownDeferred: makeDeferred(),
                isCoolingDown: true,
            });
            // Keep local reference of cooling down deferred, because the one stored
            // on `this` could be overwritten by another call to this throttle.
            const coolingDownDeferred = this.coolingDownDeferred;
            let unexpectedError;
            try {
                await coolingDownDeferred;
            } catch (error) {
                if (
                    !(error instanceof ThrottleFlushedError) ||
                    error.throttleId !== this.id
                ) {
                    // This branching should never happen.
                    // Still defined in case of programming error.
                    unexpectedError = error;
                }
            } finally {
                if (this.exists()) {
                    this.update({
                        cooldownTimer: clear(),
                        coolingDownDeferred: clear(),
                        isCoolingDown: false,
                    });
                }
            }
            if (unexpectedError) {
                throw unexpectedError;
            }
        },
    },
    fields: {
        cooldownTimer: one('Timer', {
            inverse: 'throttleOwner',
            isCausal: true,
        }),
        /**
         * Deferred of current cooling down phase in progress. Defined only when
         * there is a cooling down phase in progress. Resolved when cooling down
         * phase terminates from timeout, and rejected if flushed.
         *
         * @see ThrottleFlushedError for rejection of this deferred.
         */
        coolingDownDeferred: attr(),
        /**
         * Duration, in milliseconds, of the cool down phase.
         */
        duration: attr({
            compute: '_computeDuration',
            readonly: true,
            required: true,
        }),
        /**
         * Inner function to be invoked and throttled.
         */
        func: attr(),
        hasSilentCancelationErrors: attr({
            default: true,
        }),
        /**
         * Unique id of this throttle function. Useful for the ThrottleError
         * management, in order to determine whether these errors come from
         * this throttle or from another one (e.g. inner function makes use of
         * another throttle).
         */
        id: attr({
            compute: '_computeId',
        }),
        /**
         * Determines whether the throttle function is currently in cool down
         * phase. Cool down phase happens just after inner function has been
         * invoked, and during this time any following function call are pending
         * and will be invoked only after the end of the cool down phase (except
         * if canceled).
         */
        isCoolingDown: attr({
            default: false,
        }),
        /**
         * Deferred of a currently pending invocation to inner function. Defined
         * only during a cooling down phase and just after when throttle
         * function has been called during this cooling down phase. It is kept
         * until cooling down phase ends (either from timeout or flushed
         * throttle) or until throttle is canceled (i.e. removes pending invoke
         * while keeping cooling down phase live on).
         */
        pendingInvokeDeferred: attr(),
        threadAsThrottleNotifyCurrentPartnerTypingStatus: one('Thread', {
            inverse: 'throttleNotifyCurrentPartnerTypingStatus',
            readonly: true,
        }),
    },
});
