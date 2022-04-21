/** @odoo-module **/

import ListController from 'web.ListController';
import viewRegistry from 'web.view_registry';
import ListView from 'web.ListView';
import {ComponentWrapper} from 'web.OwlCompatibility';
import {PagePropertiesDialogWrapper} from '@website/components/dialog/page_properties';

const WebsitePageListController = ListController.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Used to set the new dialog (created by PagePropertiesDialogWrapper for page
     * record).
     */
    setPageManagerDialog(dialog) {
        this.pageManagerDialog = dialog;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _callButtonAction(attrs, record) {
        if (attrs.name === "action_optimize_seo") {
            this._goToPage(record.data.url, record.data.website_id, {
                enable_seo: true,
            });
        } else if (attrs.name === "action_manage_page") {
            this.PagePropertiesDialog = new ComponentWrapper(this, PagePropertiesDialogWrapper, {
                setPagePropertiesDialog: this.setPageManagerDialog.bind(this),
                currentPage: record.data.id,
            });
            await this.PagePropertiesDialog.mount(this.el);
            this.pageManagerDialog.open();
        } else {
            return this._super(...arguments);
        }
    },
    /**
     * @private
     */
    _goToPage(path, website, options = {}) {
        this.do_action('website.website_editor', {
            additional_context: {
                params: {
                    path: path,
                    website_id: website || '',
                    ...options,
                }
            },
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onOpenRecord(event) {
        const record = this.model.get(event.data.id, {raw: true});
        this._goToPage(record.data.url, record.data.website_id);
    },
});

const WebsitePageListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: WebsitePageListController,
    }),
});

viewRegistry.add('website_page_list', WebsitePageListView);

export default {
    WebsitePageListController: WebsitePageListController,
    WebsitePageListView: WebsitePageListView,
};
