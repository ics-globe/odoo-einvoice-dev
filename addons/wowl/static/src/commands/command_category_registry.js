/** @odoo-module **/
import { Registry } from "../core/registry";
import { _lt } from "../localization/translation";

const commandCategoryRegistry = (odoo.commandCategoryRegistry = new Registry());
commandCategoryRegistry.add("main", { label: _lt("Main Commands") }, { sequence: 10 });
commandCategoryRegistry.add("app", { label: _lt("Current App Commands") }, { sequence: 20 });
commandCategoryRegistry.add("actions", { label: _lt("More Actions") }, { sequence: 30 });
commandCategoryRegistry.add("navbar", { label: _lt("NavBar") }, { sequence: 40 });
commandCategoryRegistry.add("default", { label: _lt("Other commands") }, { sequence: 100 });
