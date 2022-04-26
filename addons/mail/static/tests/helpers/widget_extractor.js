/** @odoo-module **/

import { ComponentAdapter } from 'web.OwlCompatibility';

const { Component, onMounted, onWillUnmount } = owl;

/**
 * This class let us instanciate a widget via createWebClient and get it
 * afterwards in order to return it during tests.
 */
export class WidgetExtractor extends ComponentAdapter {
    constructor() {
        super(...arguments);
        this.env = Component.env;
        onMounted(() => {
            WidgetExtractor.currentWidget = this.widget;
        });
        onWillUnmount(() => {
            WidgetExtractor.currentWidget.destroy();
            WidgetExtractor.currentWidget = undefined;
        });
    }
}
