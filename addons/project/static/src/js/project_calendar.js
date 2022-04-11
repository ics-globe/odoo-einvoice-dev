/** @odoo-module **/

import CalendarController from 'web.CalendarController';
import CalendarModel from 'web.CalendarModel';
import CalendarView from 'web.CalendarView';
import viewRegistry from 'web.view_registry';
import { ProjectControlPanel } from '@project/js/project_control_panel';
import CalendarRenderer from 'web.CalendarRenderer';

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

    /**
    * @override
    * @private
    */
    _onPopoverShown: function($popoverElement, calendarPopover) {
        this._super.apply(this, arguments);
        calendarPopover.$fieldsList.forEach((key, value) => {
            const widgetField = key[0].lastChild.firstChild;
            if (widgetField.className.includes('o_priority')) {
                $('.card-header h4').prepend(widgetField);
                key.remove();
            }
            if (widgetField.className.includes('o_selection')) {
                $('a[name="stage_id"]').prepend(widgetField);
                key.remove();
            }
        })
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
