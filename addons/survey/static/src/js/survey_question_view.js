odoo.define('survey.QuestionFormViewDialog', function (require) {
'use strict';

var dialogs = require('web.view_dialogs');
var core = require('web.core');
var _t = core._t;


var QuestionFormViewDialog = dialogs.FormViewDialog.extend({
    /**
     * @param {Widget} parent
     * @param {Object} [options]
     * @param {string} [options.parentID] the id of the parent record. It is
     *   useful for situations such as a one2many opened in a form view dialog.
     *   In that case, we want to be able to properly evaluate domains with the
     *   'parent' key.
     * @param {integer} [options.res_id] the id of the record to open
     * @param {Object} [options.form_view_options] dict of options to pass to
     *   the Form View @todo: make it work
     * @param {Object} [options.fields_view] optional form fields_view
     * @param {boolean} [options.readonly=false] only applicable when not in
     *   creation mode
     * @param {boolean} [options.deletable=false] whether or not the record can
     *   be deleted
     * @param {boolean} [options.disable_multiple_selection=false] set to true
     *   to remove the possibility to create several records in a row
     * @param {function} [options.on_saved] callback executed after saving a
     *   record.  It will be called with the record data, and a boolean which
     *   indicates if something was changed
     * @param {function} [options.on_remove] callback executed when the user
     *   clicks on the 'Remove' button
     * @param {BasicModel} [options.model] if given, it will be used instead of
     *  a new form view model
     * @param {string} [options.recordID] if given, the model has to be given as
     *   well, and in that case, it will be used without loading anything.
     * @param {boolean} [options.shouldSaveLocally] if true, the view dialog
     *   will save locally instead of actually saving (useful for one2manys)
     * @param {function} [options._createContext] function to get context for name field
     *   useful for many2many_tags widget where we want to removed default_name field
     *   context.
     */
    init: function (parent, options) {
        var self = this;
        options = options || {};

        this.res_id = options.res_id || null;
        this.on_saved = options.on_saved || (function () {});
        this.on_remove = options.on_remove || (function () {});
        this.context = options.context;
        this._createContext = options._createContext;
        this.model = options.model;
        this.parentID = options.parentID;
        this.recordID = options.recordID;
        this.shouldSaveLocally = options.shouldSaveLocally;
        this.readonly = options.readonly;
        this.deletable = options.deletable;
        this.disable_multiple_selection = options.disable_multiple_selection;
        var oBtnRemove = 'o_btn_remove';

        var multi_select = !_.isNumber(options.res_id) && !options.disable_multiple_selection;
        var readonly = _.isNumber(options.res_id) && options.readonly;

        if (!options.buttons) {
            options.buttons = [{
                text: options.close_text || (readonly ? _t("Close") : _t("Discard")),
                classes: "btn-secondary o_form_button_cancel",
                close: true,
                click: function () {
                    if (!readonly) {
                        self.form_view.model.discardChanges(self.form_view.handle, {
                            rollback: self.shouldSaveLocally,
                        });
                    }
                },
            }];

            if (!readonly) {
                options.buttons.unshift({
                    text: options.save_text || (multi_select ? _t("Save & Close") : _t("Save")),
                    classes: "btn-primary",
                    click: async function () {
                        self._save()
                            .then(self.close.bind(self),
                                 function(error) {
                                    return Promise.reject(error);
                                });
                    }
                });

                if (multi_select) {
                    options.buttons.splice(1, 0, {
                        text: _t("Save & New"),
                        classes: "btn-primary",
                        click: async function () {
                            self._save()
                            .then(function () {
                                // reset default name field from context when Save & New is clicked, pass additional
                                // context so that when getContext is called additional context resets it
                                const additionalContext = self._createContext && self._createContext(false);
                                // This resets form data
                                self.form_view.createRecord(self.parentID, additionalContext);
                            }, function(error) {
                                return Promise.reject(error);
                            })
                            .then(function () {
                                if (!self.deletable) {
                                    return;
                                }
                                self.deletable = false;
                                self.buttons = self.buttons.filter(function (button) {
                                    return button.classes.split(' ').indexOf(oBtnRemove) < 0;
                                });
                                self.set_buttons(self.buttons);
                                self.set_title(_t("Create ") + _.str.strRight(self.title, _t("Open: ")));
                            });
                        },
                    });
                }

                var multi = options.disable_multiple_selection;
                if (!multi && this.deletable) {
                    this._setRemoveButtonOption(options, oBtnRemove);
                }
            }
        }
        this._super(parent, options);
    },
    /**
     * @private
     * @returns {Promise}
     */
    _save: async function () {
        var self = this;
        return await this.form_view.saveRecord(this.form_view.handle, {
            stayInEdit: true,
            reload: false,
            savePoint: this.shouldSaveLocally,
            viewType: 'form',
        }).then(async function (changedFields) {
            // record might have been changed by the save (e.g. if this was a new record, it has an
            // id now), so don't re-use the copy obtained before the save
            var record = self.form_view.model.get(self.form_view.handle);
            return await self.on_saved(record, !!changedFields.length);
        });
    },
})

return QuestionFormViewDialog;

});