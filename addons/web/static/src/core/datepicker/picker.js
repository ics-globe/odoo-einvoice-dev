/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";

const { Component, onWillUpdateProps, useState } = owl;
const { DateTime } = luxon;

const DAYS_OF_WEEK = [_lt("Su"), _lt("Mo"), _lt("Tu"), _lt("We"), _lt("Th"), _lt("Fr"), _lt("Sa")];
const VIEW_MODES = {
    days: "days",
    months: "months",
    years: "years",
    decades: "decades",
};

const getDateInfo = ({ day, month, year }) => {
    return {
        day,
        month,
        year,
        decade: Math.min(year / 10) + 1,
        century: Math.min(year / 100) + 1,
    };
};

export class Picker extends Component {
    setup() {
        this.state = useState({
            active: this.props.date,
            view: VIEW_MODES.days,
        });
        this.daysOfWeek = DAYS_OF_WEEK;

        this.setupDays();

        onWillUpdateProps((nextProps) => (this.state.active = nextProps.date));
    }

    get active() {
        return getDateInfo(this.state.active);
    }

    get current() {
        return getDateInfo(DateTime.local());
    }

    setupDays() {
        this.state.weeks = [];
    }

    getPickerHeader() {
        return "";
    }
}

Picker.template = "web.Picker";
Picker.props = {
    value: DateTime,
    onChange: Function,
};
