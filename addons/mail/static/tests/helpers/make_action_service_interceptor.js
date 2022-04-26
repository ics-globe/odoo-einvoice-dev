/** @odoo-module **/

import { actionService } from '@web/webclient/actions/action_service';

/**
 * Intercept action service's function calls and call the mocked function instead. The original
 * function is passed as a parameter to the mocked function.
 *
 * @param {Object} fnNameToMockedFn Object containing action service's mock functions as value
 * and their names as key.
 * @returns The action service updated with the mocked functions. Mocked methods are given
 * the original function as parameter in addition to the other parameters.
 */
export function makeActionServiceInterceptor(fnNameToMockedFn) {
    return {
        ...actionService,
        start() {
            const originalService = actionService.start(...arguments);
            const mockedActionService = { ...originalService };
            for (const fnName in fnNameToMockedFn) {
                const originalFn = originalService[fnName];
                if (originalFn) {
                    mockedActionService[fnName] = function () {
                        // explicitly set missing expected parameters to undefined in order to add the original function in
                        // the right place.
                        const args = [...arguments];
                        while (args.length < fnNameToMockedFn[fnName].length - 1) {
                            args.push(undefined);
                        }
                        return fnNameToMockedFn[fnName](...args, originalFn.bind(originalService));
                    };
                } else {
                    mockedActionService[fnName] = (...params) => fnNameToMockedFn[fnName](...params);
                }
            }
            return mockedActionService;
        },
    };
}
