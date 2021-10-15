odoo.define('survey.SurveyFormController', function (require) {
'use strict';

var FormController = require('web.FormController');
var QuestionFormViewDialog = require('survey.QuestionFormViewDialog');
var core = require('web.core');

var _t = core._t;


var SurveyFormController = FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        save_form_before_new_question: '_saveFormBeforeNewQuestion',
    }),

    _saveFormBeforeNewQuestion: async function (ev) {
        console.log("Saving survey");
        if (ev) {
            ev.stopPropagation();
        }
        // Run this pipeline synchronously before opening editor form to update/create
        return await this.saveRecord(null, {
            stayInEdit: true,
            reload: true,
        }).then(function () {
            if (ev && ev.data.callback)
                ev.data.callback();
            return Promise.resolve("OK")
        }).catch(reason => {
            return Promise.reject(reason);
        })
    },

    _onOpenOne2ManyRecord: async function (ev) {
        ev.stopPropagation();
        var data = ev.data;
        var record;
        if (data.id) {
            record = this.model.get(data.id, {raw: true});
        }

        // Sync with the mutex to wait for potential onchanges
        await this.model.mutex.getUnlockedDef();
        new QuestionFormViewDialog(this, {
            context: data.context,
            domain: data.domain,
            fields_view: data.fields_view,
            model: this.model,
            on_saved: data.on_saved,
            on_remove: data.on_remove,
            parentID: data.parentID,
            readonly: data.readonly,
            deletable: record ? data.deletable : false,
            disable_multiple_selection: data.disable_multiple_selection,
            recordID: record && record.id,
            res_id: record && record.res_id,
            res_model: data.field.relation,
            shouldSaveLocally: false,
            title: (record ? _t("Open: ") : _t("Create ")) + (ev.target.string || data.field.string),
        }).open();
    },
});

return SurveyFormController;

});
