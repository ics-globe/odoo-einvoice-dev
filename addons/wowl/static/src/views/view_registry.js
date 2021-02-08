/** @odoo-module **/
import { Registry } from "../core/registry";
import CalendarView from "./calendar/view";
import { GraphView } from "./graph/graph_view";
import { ListView } from "./list/list_view";
export const viewRegistry = new Registry();
viewRegistry.add("calendar", CalendarView);
// viewRegistry.add("form", FormView);
viewRegistry.add("graph", GraphView);
viewRegistry.add("list", ListView);
