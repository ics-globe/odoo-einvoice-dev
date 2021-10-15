odoo.define('survey.question_page_one2many', function (require) {
"use strict";

var Context = require('web.Context');
var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
var FieldRegistry = require('web.field_registry');
var ListRenderer = require('web.ListRenderer');
var config = require('web.config');

var SectionListRenderer = ListRenderer.extend({
    init: function (parent, state, params) {
        this.sectionFieldName = "is_page";
        this._super.apply(this, arguments);
    },
    _checkIfRecordIsSection: function (id) {
        var record = this._findRecordById(id);
        return record && record.data[this.sectionFieldName];
    },
    _findRecordById: function (id) {
        return _.find(this.state.data, function (record) {
            return record.id === id;
        });
    },
    /**
     * Allows to hide specific field in case the record is a section
     * and, in this case, makes the 'title' field take the space of all the other
     * fields
     * @private
     * @override
     * @param {*} record
     * @param {*} node
     * @param {*} index
     * @param {*} options
     */
    _renderBodyCell: function (record, node, index, options) {
        var $cell = this._super.apply(this, arguments);

        var isSection = record.data[this.sectionFieldName];

        if (isSection) {
            if (node.attrs.widget === "handle" || node.attrs.name === "random_questions_count") {
                return $cell;
            } else if (node.attrs.name === "title") {
                var nbrColumns = this._getNumberOfCols();
                if (this.handleField) {
                    nbrColumns--;
                }
                if (this.addTrashIcon) {
                    nbrColumns--;
                }
                if (record.data.questions_selection === "random") {
                    nbrColumns--;
                }
                $cell.attr('colspan', nbrColumns);
            } else {
                $cell.removeClass('o_invisible_modifier');
                return $cell.addClass('o_hidden');
            }
        }
        return $cell;
    },
    /**
     * Adds specific classes to rows that are sections
     * to apply custom css on them
     * @private
     * @override
     * @param {*} record
     * @param {*} index
     */
    _renderRow: function (record, index) {
        var $row = this._super.apply(this, arguments);
        if (record.data[this.sectionFieldName]) {
            $row.addClass("o_is_section");
        }
        return $row;
    },
    /**
     * Adding this class after the view is rendered allows
     * us to limit the custom css scope to this particular case
     * and no other
     * @private
     * @override
     */
    _renderView: function () {
        var def = this._super.apply(this, arguments);
        var self = this;
        return def.then(function () {
            self.$('table.o_list_table').addClass('o_section_list_view');
        });
    },
    // Handlers
    /**
     * Overridden to allow different behaviours depending on
     * the row the user clicked on.
     * If the row is a section: edit inline
     * else use a normal modal
     * @private
     * @override
     * @param {*} ev
     */
    _onRowClicked: function (ev) {
        var parent = this.getParent();
        var recordId = $(ev.currentTarget).data('id');
        var is_section = this._checkIfRecordIsSection(recordId);
        if (is_section && parent.mode === "edit") {
            this.editable = "bottom";
        } else {
            this.editable = null;
        }
        this._super.apply(this, arguments);
    },
    /**
     * Overridden to allow different behaviours depending on
     * the cell the user clicked on.
     * If the cell is part of a section: edit inline
     * else use a normal edit modal
     * @private
     * @override
     * @param {*} ev
     */
    _onCellClick: function (ev) {
        var parent = this.getParent();
        var recordId = $(ev.currentTarget.parentElement).data('id');
        var is_section = this._checkIfRecordIsSection(recordId);
        if (is_section && parent.mode === "edit") {
            this.editable = "bottom";
        } else {
            this.editable = null;
            this.unselectRow();
        }
        this._super.apply(this, arguments);
    },
    /**
     * In this case, navigating in the list caused issues.
     * For example, editing a section then pressing enter would trigger
     * the inline edition of the next element in the list. Which is not desired
     * if the next element ends up being a question and not a section
     * @override
     * @param {*} ev
     */
    _onNavigationMove: function (ev) {
        this.unselectRow();
    },
});

var SectionFieldOne2Many = FieldOne2Many.extend({
    init: function (parent, name, record, options) {
        this._super.apply(this, arguments);
        this.sectionFieldName = "is_page";
        this.rendered = false;
        this.disable_multiple_selection = false;
    },
    /**
     * Overridden to use our custom renderer
     * @private
     * @override
     */
    _getRenderer: function () {
        if (this.view.arch.tag === 'tree') {
            return SectionListRenderer;
        }
        return this._super.apply(this, arguments);
    },

    /**
     * Overridden to allow different behaviours depending on
     * the object we want to add. Adding a section would be done inline
     * while adding a question would render a modal.
     * @private
     * @override
     * @param {*} ev
     */
    _onAddRecord: function (ev) {
        this.editable = null;
        if (!config.device.isMobile) {
            var context_str = ev.data.context && ev.data.context[0];
            var context = new Context(context_str).eval();
            if (context['default_' + this.sectionFieldName]) {
                this.editable = "bottom";
                this._super.apply(this, arguments);
            } else {
                var self = this;
                var fnSuper = this._super;
                var fnArguments = arguments;
                ev.data = { 'disable_multiple_selection': false };
                // ensures the survey exists
                this.trigger_up('save_form_before_new_question', {
                    callback: function () { fnSuper.apply(self, fnArguments); }
                });
            }
        } else {
            this._super.apply(this, arguments);
        }
    },

    /**
     * Overridden to save the survey after each question
     * @private
     * @param {*} data
     * @override
     */
     _addCreateRecordRow(data) {
        const self = this;
        if (this.editable || data.forceEditable) {
            if (!this.activeActions.create) {
                if (data.onFail) {
                    data.onFail();
                }
            } else if (!this.creatingRecord) {
                this.creatingRecord = true;
                this.trigger_up('edited_list', { id: this.value.id });
                this._setValue({
                    operation: 'CREATE',
                    position: this.editable || data.forceEditable,
                    context: data.context,
                }, {
                    allowWarning: data.allowWarning
                }).then(function () {
                    self.creatingRecord = false;
                }).then(function (){
                    if (data.onSuccess){
                        data.onSuccess();
                    }
                }).guardedCatch(function() {
                    self.creatingRecord = false;
                });
            }
        } else {
            this._openFormDialog({
                context: data.context && data.context[0],
                disable_multiple_selection: data.disable_multiple_selection,
                on_saved: async function (record) {
                    let that = this;
                    self._setValue({operation: 'ADD', id: record.id});
                    await self.renderer.commitChanges(record.id)
                        .then(async function () {
                        return await self._saveLine(record.id, that.parent)
                    })
                }
            })
        }
    },
    /**
     * Saves the line associated to the given recordID. If the line is valid,
     * it only has to be switched to readonly mode as all the line changes have
     * already been notified to the model so that they can be saved in db if the
     * parent view is actually saved. If the line is not valid, the line is to
     * be discarded if the user agrees (this behavior is not a list editable
     * one but a x2m one as it is made to replace the "discard" button which
     * exists for list editable views).
     *
     * @private
     * @override Overridden to make it run synchonously to have all previous data
     *           at hand for the next questions (dependencies).
     * @param {string} recordID
     * @param controller
     * @returns {Promise} resolved if the line was properly saved or discarded.
     *                     rejected if the line could not be saved and the user
     *                     did not agree to discard.
     */
    _saveLine: async function (recordID, controller) {
        var self = this;
        return await new Promise(async function (resolve, reject) {
            var fieldNames = self.renderer.canBeSaved(recordID);
            if (fieldNames.length) {
                self.trigger_up('discard_changes', {
                    recordID: recordID,
                    onSuccess: resolve,
                    onFailure: reject,
                });
            } else {
                // Make that synchronous
                return await self.renderer.setRowMode(recordID, 'readonly')
                    .then(async function() {
                        if (controller) {
                            await controller._saveFormBeforeNewQuestion().then(resolve, reject);
                        } else { // undefined when editing in tree view, so unnecessary as no special attributes are set.
                            resolve();
                        }
                    });
            }
        }).then(async function () {
            self._updateControlPanel({ size: self.value.count });
            var newEval = self._evalColumnInvisibleFields();
            if (!_.isEqual(self.currentColInvisibleFields, newEval)) {
                self.currentColInvisibleFields = newEval;
                self.renderer.updateState(self.value, {
                    columnInvisibleFields: self.currentColInvisibleFields,
                });
            }
        });
    },
});

FieldRegistry.add('question_page_one2many', SectionFieldOne2Many);
});
