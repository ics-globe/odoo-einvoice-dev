/** @odoo-module **/

import { Markup } from 'web.utils';
import { registry } from "@web/core/registry";

export const iapNotificationService = {
    dependencies: ["bus_service", "notification"],

    start(env, { notification, bus_service }) {
        env.bus.on("WEB_CLIENT_READY", null, async () => {
            bus_service.onNotification(this, (notifications) => {
                for (const { payload, type } of notifications) {
                    if (type === 'iap_notification') {
                        if (payload.error_type == 'success') {
                            displaySuccessIapNotification(payload);
                        } else if (payload.error_type == 'danger') {
                            displayFailureIapNotification(payload);
                        }
                    }
                }
            });
            bus_service.startBus();
        });

        /**
         * Displays the IAP success notification on user's screen
         */
        function displaySuccessIapNotification(notif) {
            notification.add(notif.title, {
                type: notif.error_type,
            });
        }

        /**
         * Displays the IAP failure notification on user's screen
         */
        function displayFailureIapNotification(notif) {
            const message = Markup`<a class='btn btn-link' href='${notif.url}' target='_blank' ><i class='fa fa-arrow-right'></i> ${env._t("Buy more credits")}</a>`;
            notification.add(message, {
                type: notif.error_type,
                title: notif.title
            });
        }
    }
};

registry.category("services").add("iapNotification", iapNotificationService);
