/** @odoo-module **/

import { evalDomain } from "@web/views/relational_model";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ListRenderer } from "@web/views/list/list_renderer";
import { Pager } from "@web/core/pager/pager";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { useService, useOwnedDialogs } from "@web/core/utils/hooks";
import { useX2M } from "./x2m_utils";

const { Component } = owl;

const X2M_RENDERERS = {
    list: ListRenderer,
    kanban: KanbanRenderer,
};

export class X2ManyField extends Component {
    setup() {
        this.user = useService("user");
        this.viewService = useService("view");

        this.addDialog = useOwnedDialogs();

        this.activeField = this.props.record.activeFields[this.props.name];
        this.field = this.props.record.fields[this.props.name];

        this.isMany2Many =
            this.field.type === "many2many" || this.activeField.widget === "many2many";

        this.addButtonText = this.activeField.attrs["add-label"] || this.env._t("Add");

        this.viewMode = this.activeField.viewMode;
        this.Renderer = X2M_RENDERERS[this.viewMode];

        const { selectCreate, addRecord, activeActions, openRecord } = useX2M({
            getRecord: () => this.props.record,
            fieldName: this.props.name,
            isMany2Many: this.isMany2Many,
        });
        this.selectCreate = selectCreate;
        this.onAdd = addRecord;
        this.activeActions = activeActions;
        this.openRecord = (record) => openRecord(record, this.props.readonly ? "readonly" : "edit");
    }

    get list() {
        return this.props.value;
    }

    get rendererProps() {
        const archInfo = this.activeField.views[this.viewMode];
        let columns;
        if (this.viewMode === "list") {
            // handle column_invisible modifiers
            // first remove (column_)invisible buttons in button_groups
            columns = archInfo.columns.map((col) => {
                if (col.type === "button_group") {
                    const buttons = col.buttons.filter((button) => {
                        return !this.evalColumnInvisibleModifier(button.modifiers);
                    });
                    return { ...col, buttons };
                }
                return col;
            });
            // then filter out (column_)invisible fields and empty button_groups
            columns = columns.filter((col) => {
                if (col.type === "field") {
                    return !this.evalColumnInvisibleModifier(col.modifiers);
                } else if (col.type === "button_group") {
                    return col.buttons.length > 0;
                }
                return true;
            });
        }
        const props = {
            activeActions: this.activeActions,
            editable: this.props.record.isInEdition && archInfo.editable,
            archInfo: { ...archInfo, columns },
            list: this.list,
            openRecord: this.openRecord,
            onAdd: this.onAdd,
        };
        if (this.viewMode === "kanban") {
            props.readonly = this.props.readonly;
        }
        return props;
    }

    get displayAddButton() {
        const { canCreate, canLink } = this.activeActions;
        return (
            this.viewMode === "kanban" &&
            (canLink !== undefined ? canLink : canCreate) &&
            !this.props.readonly
        );
    }

    get pagerProps() {
        const list = this.list;
        return {
            offset: list.offset,
            limit: list.limit,
            total: list.count,
            onUpdate: async ({ offset, limit }) => {
                const initialLimit = this.list.limit;
                const unselected = await list.unselectRecord();
                if (unselected) {
                    if (initialLimit === limit && initialLimit === this.list.limit + 1) {
                        // Unselecting the edited record might have abandonned it. If the page
                        // size was reached before that record was created, the limit was temporarily
                        // increased to keep that new record in the current page, and abandonning it
                        // decreased this limit back to it's initial value, so we keep this into
                        // account in the offset/limit update we're about to do.
                        offset -= 1;
                        limit -= 1;
                    }
                    await list.load({ limit, offset });
                    this.render();
                }
            },
            withAccessKey: false,
        };
    }

    evalColumnInvisibleModifier(modifiers) {
        if ("column_invisible" in modifiers) {
            return evalDomain(modifiers.column_invisible, this.list.evalContext);
        }
        return false;
    }
}

X2ManyField.components = { Pager };
X2ManyField.props = { ...standardFieldProps };
X2ManyField.template = "web.X2ManyField";
X2ManyField.useSubView = true;
registry.category("fields").add("one2many", X2ManyField);
registry.category("fields").add("many2many", X2ManyField);
