/** @odoo-module **/
import { ErrorDialog } from "@web/core/errors/error_dialogs";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { UncaughtPromiseError } from "@web/core/errors/error_service";

//--------------------------------------------------------------------------
// Errors
//--------------------------------------------------------------------------

export class WebsocketError extends Error {
    constructor(params) {
        super();
        this.name = "WEBSOCKET_ERROR";
        this.type = "server";
        this.exceptionName = params.name;
        this.message = params.message;
        this.debug = params.debug;
    }
}

//--------------------------------------------------------------------------
// Errors Dialogs
//--------------------------------------------------------------------------

export class WebsocketErrorDialog extends ErrorDialog {
    setup() {
        super.setup();
        this.title = this.env._t("Odoo Server Error");
        this.traceback = this.props.debug;
        this.message = this.props.message;
    }

    onClickClipboard() {
        browser.navigator.clipboard.writeText(
            `${this.props.exceptionName}\n${this.props.message}\n${this.traceback}`
        );
    }
}


//--------------------------------------------------------------------------
// Error Handlers
//--------------------------------------------------------------------------

const errorDialogRegistry = registry.category("error_dialogs");
const errorNotificationRegistry = registry.category("error_notifications");

export function websocketErrorHandler(env, error, originalError) {
    if (!(error instanceof UncaughtPromiseError)) {
        return false;
    }
    if (originalError instanceof WebsocketError) {
        let errorComponent;
        const exceptionName = originalError.exceptionName;
        if (errorNotificationRegistry.contains(exceptionName)) {
            const notif = errorNotificationRegistry.get(exceptionName);
            env.services.notification.add(notif.message || originalError.message, notif);
            return true;
        }
        if (errorDialogRegistry.contains(exceptionName)) {
            errorComponent = errorDialogRegistry.get(exceptionName);
        }
        env.services.dialog.add(errorComponent || WebsocketErrorDialog, {
            message: originalError.message,
            name: originalError.name,
            exceptionName: originalError.exceptionName,
            debug: originalError.debug,
        });
        return true;
    }
}
registry.category("error_handlers").add("WebsocketError", websocketErrorHandler);
