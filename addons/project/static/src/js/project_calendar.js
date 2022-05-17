/** @odoo-module **/

import CalendarController from 'web.CalendarController';
import CalendarModel from 'web.CalendarModel';
import CalendarView from 'web.CalendarView';
import viewRegistry from 'web.view_registry';
import { ProjectControlPanel } from '@project/js/project_control_panel';
import CalendarRenderer from 'web.CalendarRenderer';
import { qweb as QWeb }from 'web.core';
import CalendarPopover from 'web.CalendarPopover';

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
const projectCalendarPopover = CalendarPopover.extend({
    template: 'Project.event.popover',

    init () {debugger
        this._super(...arguments);
        const kanban_state = this.displayFields.kanban_state;
        const stage_id = this.displayFields.stage_id;
        // this.allocated_hours = fieldUtils.format.float_time(this.event.extendedProps.record.allocated_hours);
        // this.allocated_percentage = fieldUtils.format.float(this.event.extendedProps.record.allocated_percentage);
    },

    _processFields() {debugger
        var self = this;

        if (!CalendarPopover.prototype.origDisplayFields) {
            CalendarPopover.prototype.origDisplayFields = _.extend({}, this.displayFields);
        } else {
            this.displayFields = _.extend({}, CalendarPopover.prototype.origDisplayFields);
        }

        _.each(this.displayFields, function(def, field) {
            if (self.event.extendedProps && self.event.extendedProps.record && !self.event.extendedProps.record[field]) {
                delete self.displayFields[field];
            } 
        });

        return this._super(...arguments);
    }
    
//     // start: function () {
//     //     this._super(...arguments);

//     //     // ('li a[name="stage_id"]')
//     //     debugger;
//     //     let fields_secondary = this.el.querySelector('.o_cw_popover_fields_secondary');
//     //     let fieldList = fields_secondary.querySelectorAll('li')
//     //     let stateList;
//     //     let stageList;
//     //     for( let i=0; i<fieldList.length; i++){
//     //         if(!stageList)
//     //             stageList = fieldList[i].querySelector('a[name="stage_id"]');
//     //         if(!stateList)
//     //             stateList = fieldList[i].querySelector( 'div[name="kanban_state"]');            
//     //     }

//     //     if( stageList && stateList) {
//     //         stageList.parentNode.before(stateList.parentNode);
//     //     }
//         // var self = this;
//         // // for( const element in this.$fieldsList) {
//         // //     // if (element.)
//         // // }
//         // this.displayFields.stage_id.attrs.name=this.displayFields.kanban_state.attrs.widget
//         // // this.$fieldsList[5][0].innerHTML = this.$fieldsList[6][0].children[1].innerHTML + this.$fieldsList[5][0].innerHTML
// //     },
});

const ProjectCalendarRenderer = CalendarRenderer.extend({
    // template: "Project.CalendarView.extend",
    config: Object.assign({}, CalendarRenderer.prototype.config, {
        CalendarPopover: projectCalendarPopover,
    }),
    
    // _getPopoverParams: function (eventData) {
    //     const params = this._super(...arguments);
    //     let PriorityIcon;
    //     let KanbanIcon;
    //     const priority = eventData.extendedProps.record.priority;
    //     const kanban_state = eventData.extendedProps.record.kanban_state;
    //     const stage_id = eventData.extendedProps.record.stage_id
        
    //     if (kanban_state === 'blocked') {
    //         KanbanIcon = 'o_status d-inline-block align-middle o_status_red';
    //     } else if(kanban_state === 'normal') {
    //         KanbanIcon = 'o_status d-inline-block align-middle';
    //     }else if(kanban_state === 'done'){
    //         KanbanIcon = 'o_status d-inline-block align-middle o_status_green';
    //     }

        

    //     if (priority === '1') {
    //         PriorityIcon = 'fa-star color_yellow';
    //     } else if(priority) {
    //         PriorityIcon = 'fa-star-o';
    //     }

    //     params.template = QWeb.render('project.calendar.popover.placeholder', {
    //         PriorityIcon: PriorityIcon,
    //         KanbanIcon: KanbanIcon,
    //     });
    //     return params;
    // },

    // _onPopoverShown: function ($popoverElement, calendarPopover) {debugger
    //     var $popover = $($popoverElement.data('bs.popover').tip);
    //     this.$pop = $popover.find('.o_cw_body')
    //     const params = this._super(...arguments);
    //     // const $popover = $($popoverElement.data('bs.popover').tip);
    //     // const span = $popover.find('div[name="kanban_state"] span')[0];
    //     // $popover.find('a[name="stage_id"]').prepend(span);
    //     // // $popover.find('div[name="kanban_state"]').closest('.list-group-item').remove();
    // },
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
        CalendarPopover: projectCalendarPopover,
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
