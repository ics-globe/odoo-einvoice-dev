/** @odoo-module **/

export function makeMessagingValuesProviderService(values = {}) {
    return {
        start() {
            return {
                get() {
                    return values;
                },
            };
        },
    };
}
