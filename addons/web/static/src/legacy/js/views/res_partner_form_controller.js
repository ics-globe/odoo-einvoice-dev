/** @odoo-module alias=web.ResPartnerFormController **/

import { _t } from 'web.core';
import FormController from 'web.FormController';
import ResPartnerFormViewDialog from 'web.ResPartnerFormViewDialog';


const ResPartnerFormController = FormController.extend({

    /**
     * @override
     */
    _onOpenOne2ManyRecord: async function (ev) {
        ev.stopPropagation();
        const data = ev.data;
        const record = data.id ? this.model.get(data.id, {raw: true}) : null;

        // Sync with the mutex to wait for potential onchanges
        await this.model.mutex.getUnlockedDef();

        new ResPartnerFormViewDialog(this, {
            context: data.context,
            domain: data.domain,
            fields_view: data.fields_view,
            model: this.model,
            on_saved: data.on_saved,
            on_remove: data.on_remove,
            parentID: data.parentID,
            readonly: data.readonly,
            editable: data.editable,
            deletable: record ? data.deletable : false,
            disable_multiple_selection: data.disable_multiple_selection,
            recordID: record && record.id,
            res_id: record && record.res_id,
            res_model: data.field.relation,
            shouldSaveLocally: true,
            title: (record ? _t("Open: ") : _t("Create ")) + (ev.target.string || data.field.string),
        }).open();
    },

});

export default ResPartnerFormController;
