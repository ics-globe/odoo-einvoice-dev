/** @odoo-module **/

import { ModelManager } from '@mail/model/model_manager';

export const messagingService = {
    dependencies: [
        'ui',
        'effect',
        'router',
        'orm',
        'rpc',
        'legacy_bus_service',
        'localization',
        'messagingValuesProvider',
        'user',
        'wowlEnvProviderService',
    ],

    start(env, { messagingValuesProvider }) {
        const modelManager = new ModelManager(env);
        this._startModelManager(modelManager, messagingValuesProvider.get());

        return {
            /**
             * Returns the messaging record once it is initialized. This method
             * should be considered the main entry point to the messaging system
             * for outside code.
             *
             * @returns {mail.messaging}
             **/
            async get() {
                return modelManager.getMessaging();
            },
            modelManager,
        };
    },
    /**
     * Separate method to control creation delay in tests.
     *
     * @private
     */
    _startModelManager(modelManager, messagingValues) {
        modelManager.start(messagingValues);
    },
};
