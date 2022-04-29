/** @odoo-module */
import { makeContext } from "@web/core/context";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { X2ManyFieldDialog } from "@web/fields/x2m_field_dialog";

import { FormArchParser, loadSubViews } from "@web/views/form/form_view";
import { sprintf } from "@web/core/utils/strings";
import { evalDomain } from "@web/views/basic_relational_model";

async function getFormViewInfo({ list, activeField, viewService, userService }) {
    let formViewInfo = activeField.views.form;
    const comodel = list.resModel;
    if (!formViewInfo) {
        const { fields, views } = await viewService.loadViews({
            context: {},
            resModel: comodel,
            views: [[false, "form"]],
        });
        const archInfo = new FormArchParser().parse(views.form.arch, fields);
        formViewInfo = { ...archInfo, fields }; // should be good to memorize this on activeField
    }

    await loadSubViews(
        formViewInfo.activeFields,
        formViewInfo.fields,
        {}, // context
        comodel,
        viewService,
        userService
    );

    return formViewInfo;
}

function prepareActiveActions({ activeField, isMany2Many, optionsExtractor }) {
    const viewMode = activeField.viewMode;
    let { options, views } = activeField;
    if (optionsExtractor) {
        options = optionsExtractor(activeField);
    }
    const subViewInfo = views[viewMode];

    function compute(record, remove) {
        // activeActions computed by getActiveActions is of the form
        // interface ActiveActions {
        //     edit: Boolean;
        //     create: Boolean;
        //     delete: Boolean;
        //     duplicate: Boolean;
        // }

        // options set on field is of the form
        // interface Options {
        //     create: Boolean;
        //     delete: Boolean;
        //     link: Boolean;
        //     unlink: Boolean;
        // }

        // We need to take care of tags "control" and "create" to set create stuff
        const { evalContext } = record;

        let canCreate = "create" in options ? evalDomain(options.create, evalContext) : true;
        canCreate = canCreate && (viewMode ? subViewInfo.activeActions.create : true);

        let canDelete = "delete" in options ? evalDomain(options.delete, evalContext) : true;
        canDelete = canDelete && (viewMode ? subViewInfo.activeActions.delete : true);

        let canLink = "link" in options ? evalDomain(options.link, evalContext) : true;
        let canUnlink = "unlink" in options ? evalDomain(options.unlink, evalContext) : true;

        let canWrite = "write" in options ? options.write : false;

        const result = { canCreate, canDelete };
        if (isMany2Many) {
            Object.assign(result, { canLink, canUnlink, canWrite });
        }
        if ((isMany2Many && canUnlink) || (!isMany2Many && canDelete)) {
            result.onDelete = remove;
        }
        return result;
    }
    return compute;
}

function makeCrud(model, isMany2Many) {
    const operation = isMany2Many ? "FORGET" : "DELETE";
    async function remove(list, record) {
        await list.delete(record.id, operation);
    }

    async function saveToList(list, recordOrResIds) {
        await list.add(recordOrResIds, { isM2M: isMany2Many });
    }

    async function update(list, record) {
        await model.updateRecord(list, record, { isM2M: isMany2Many });
    }

    return { remove, saveToList, update };
}

export function useX2M({ getRecord, fieldName, isMany2Many, optionsExtractor }) {
    const env = owl.useEnv();

    let record = getRecord();
    let list = record.data[fieldName];
    const model = record.model;

    const { remove, saveToList, update } = makeCrud(model, isMany2Many);

    const activeField = record.activeFields[fieldName];
    const viewMode = activeField.viewMode;

    const editable = viewMode && activeField.views[viewMode].editable;

    const computeActiveActions = prepareActiveActions({
        activeField,
        isMany2Many,
        optionsExtractor,
    });
    const activeActions = {};
    owl.onWillUpdateProps((nextProps) => {
        record = getRecord(nextProps);
        list = record.data[fieldName];
    });

    owl.onWillRender(() => {
        Object.keys(activeActions).forEach((k) => delete activeActions[k]);
        Object.assign(
            activeActions,
            computeActiveActions(record, (record) => remove(list, record))
        );
    });

    const addDialog = useOwnedDialogs();

    async function openRecord(record, mode) {
        const form = await getFormViewInfo({ list, activeField, viewService, userService });
        const newRecord = await list.model.duplicateDatapoint(record, {
            mode,
            viewMode: "form",
            fields: { ...form.fields },
            views: { form },
        });
        const { canDelete, onDelete } = activeActions;
        addDialog(X2ManyFieldDialog, {
            archInfo: form,
            record: newRecord,
            save: async (record, { saveAndNew }) => {
                if (record.id === newRecord.id) {
                    await update(list, record);
                } else {
                    await saveToList(list, record);
                }
                if (saveAndNew) {
                    return model.addNewRecord(list, {
                        context: list.context,
                        resModel: list.resModel,
                        activeFields: form.activeFields,
                        fields: { ...form.fields },
                        views: { form },
                        mode: "edit",
                        viewType: "form",
                    });
                }
            },
            title: sprintf(env._t("Open: %s"), activeField.string),
            delete: viewMode === "kanban" && canDelete ? () => onDelete(record) : null,
        });
    }

    function selectCreate(context) {
        const domain = [
            ...record.getFieldDomain(fieldName).toList(),
            "!",
            ["id", "in", list.currentIds],
        ];
        context = makeContext([record.getFieldContext(fieldName), context]);
        addDialog(SelectCreateDialog, {
            title: env._t("Select records"),
            noCreate: !activeActions.canCreate,
            multiSelect: activeActions.canLink, // LPE Fixme
            resModel: list.resModel,
            context,
            domain,
            onSelected: (resIds) => {
                return saveToList(list, resIds);
            },
            onCreateEdit: () => addRecord(context),
        });
    }

    const viewService = useService("view");
    const userService = useService("user");

    let creatingRecord = false;

    async function addRecord(context) {
        if (editable) {
            if (!creatingRecord) {
                creatingRecord = true;
                try {
                    await list.addNew({ context, mode: "edit", position: editable });
                } finally {
                    creatingRecord = false;
                }
            }
        } else {
            const form = await getFormViewInfo({ list, activeField, viewService, userService });
            const recordParams = {
                context: makeContext([list.context, context]),
                resModel: list.resModel,
                activeFields: form.activeFields,
                fields: { ...form.fields },
                views: { form },
                mode: "edit",
                viewType: "form",
            };
            const record = await model.addNewRecord(list, recordParams);
            addDialog(X2ManyFieldDialog, {
                archInfo: form,
                record,
                save: async (record, { saveAndNew }) => {
                    await saveToList(list, record);
                    if (saveAndNew) {
                        return model.addNewRecord(list, recordParams);
                    }
                },
                title: sprintf(env._t("Open: %s"), activeField.string),
            });
        }
    }

    return {
        activeActions,
        openRecord,
        selectCreate,
        addRecord: isMany2Many ? selectCreate : addRecord,
    };
}
