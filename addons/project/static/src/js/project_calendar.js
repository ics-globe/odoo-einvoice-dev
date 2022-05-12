/** @odoo-module **/

import CalendarController from 'web.CalendarController';
import CalendarModel from 'web.CalendarModel';
import CalendarView from 'web.CalendarView';
import viewRegistry from 'web.view_registry';
import { ProjectControlPanel } from '@project/js/project_control_panel';
import CalendarRenderer from 'web.CalendarRenderer';
import { qweb as QWeb }from 'web.core';


const ProjectCalendarController = CalendarController.extend({
    _renderButtonsParameters() {
        return Object.assign({}, this._super(...arguments), {scaleDrop: true});
    },

    /**
     * @private
     * @param {OdooEvent} event
     */
    _onChangeDate: function (event) {
        this._super.apply(this, arguments);
        this.model.setScale('month');
        this.model.setDate(event.data.date);
        this.reload();
    },
});

const ProjectCalendarRenderer = CalendarRenderer.extend({

    _getPopoverParams: function (eventData) {debugger
        const params = this._super(...arguments);
        let PriorityIcon;
        const priority = eventData.extendedProps.record.priority;

        if (priority === '1') {
            PriorityIcon = 'fa-star color_yellow';
        } else if(priority) {
            PriorityIcon = 'fa-star-o';
        }

        params.template = QWeb.render('project.calendar.popover.placeholder', {
            PriorityIcon: PriorityIcon,
        });
        return params;
    },
});
const ProjectCalendarModel = CalendarModel.extend({
    /**
     * @private
     * @override
     */
    _getFullCalendarOptions: function () {
        const options = this._super(...arguments);
        options.eventDurationEditable = false;
        return options;
    }
})

export const ProjectCalendarView = CalendarView.extend({
    config: Object.assign({}, CalendarView.prototype.config, {
        Controller: ProjectCalendarController,
        ControlPanel: ProjectControlPanel,
        Renderer: ProjectCalendarRenderer,
        Model: ProjectCalendarModel,
    }),

    /**
    * @override
    */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);
        this.controllerParams.displayName += " - Tasks by Deadline";
    }
});

viewRegistry.add('project_calendar', ProjectCalendarView);
