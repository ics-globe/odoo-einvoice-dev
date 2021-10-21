/** @odoo-module **/

import { Picker } from "@web/core/datepicker/picker";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { useAutofocus } from "@web/core/utils/hooks";

const { Component, onMounted, onWillUpdateProps, useExternalListener, useRef, useState } = owl;
const { DateTime } = luxon;

const formatters = registry.category("formatters");
const parsers = registry.category("parsers");

let datePickerId = 0;

/**
 * Date picker
 *
 * This component exposes the API of the tempusdominus datepicker library.
 * As such, its template is a simple input that will open the TD datepicker
 * when clicked on. The component will also synchronize any user-input value
 * with the library widget and vice-versa.
 *
 * Note that all props given to this component will be passed as arguments to
 * instantiate the picker widget. Also any luxon date is automatically
 * stringified since tempusdominus only works with moment objects.
 * @extends Component
 */
export class DatePicker extends Component {
    setup() {
        this.root = useRef("root");
        this.inputRef = useRef("input");
        this.state = useState({
            showPicker: false,
            warning: false,
        });

        this.datePickerId = `o_datepicker_${datePickerId++}`;

        this.initFormat();
        this.setDate(this.props);

        useAutofocus();
        useExternalListener(window, "click", this.onWindowClick);
        useExternalListener(window, "scroll", this.onWindowScroll);

        onMounted(() => this.updateInput());
        onWillUpdateProps((nextProps) => {
            for (const prop in nextProps) {
                if (this.props[prop] !== nextProps[prop] && prop === "date") {
                    this.setDate(nextProps);
                    this.updateInput();
                }
            }
        });
    }

    //---------------------------------------------------------------------
    // Getters
    //---------------------------------------------------------------------

    get options() {
        return {
            // Fallback to default localization format in `core/l10n/dates.js`.
            format: this.props.format,
            locale: this.props.locale || this.date.locale,
            timezone: this.isLocal,
        };
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    /**
     * Initialises formatting and parsing parameters
     */
    initFormat() {
        this.defaultFormat = localization.dateFormat;
        this.format = formatters.get("date");
        this.parse = parsers.get("date");
        this.isLocal = false;
    }

    /**
     * Sets the current date value. If a locale is provided, the given date
     * will first be set in that locale.
     * @param {object} params
     * @param {DateTime} params.date
     * @param {string} [params.locale]
     */
    setDate({ date, locale }) {
        this.date = locale ? date.setLocale(locale) : date;
    }

    /**
     * Updates the input element with the current formatted date value.
     */
    updateInput() {
        try {
            this.inputRef.el.value = this.format(this.date, this.options);
        } catch (_err) {
            // Do nothing
        }
    }

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    onInputClick() {
        this.state.showPicker = true;
    }

    /**
     * Called either when the input value has changed or when the boostrap
     * datepicker is closed. The onDateTimeChanged prop is only called if the
     * date value has changed.
     */
    onDateChange() {
        return this.updateValue(this.inputRef.el.value);
    }

    updateValue(value) {
        try {
            const date = this.parse(value, this.options);
            if (!date.equals(this.props.date)) {
                this.state.warning = date > DateTime.local();
                this.props.onDateTimeChanged(date);
            }
        } catch (_err) {
            // Reset to default (= given) date.
            this.updateInput();
        }
    }

    onWindowClick(ev) {
        if (!this.root.el.contains(ev.target)) {
            this.state.showPicker = false;
        }
    }

    /**
     * @param {Event} ev
     */
    onWindowScroll(ev) {
        if (ev.target !== this.inputRef.el) {
            this.state.showPicker = false;
        }
    }
}

DatePicker.components = { Picker };
DatePicker.defaultProps = {
    calendarWeeks: true,
    icons: {
        clear: "fa fa-delete",
        close: "fa fa-check primary",
        date: "fa fa-calendar",
        down: "fa fa-chevron-down",
        next: "fa fa-chevron-right",
        previous: "fa fa-chevron-left",
        time: "fa fa-clock-o",
        today: "fa fa-calendar-check-o",
        up: "fa fa-chevron-up",
    },
    maxDate: DateTime.fromObject({ year: 9999, month: 12, day: 31 }),
    minDate: DateTime.fromObject({ year: 1000 }),
    useCurrent: false,
    widgetParent: "body",
};
DatePicker.props = {
    // Components props
    onDateTimeChanged: Function,
    date: DateTime,
    warn_future: { type: Boolean, optional: true },
    // Bootstrap datepicker options
    buttons: {
        type: Object,
        shape: {
            showClear: Boolean,
            showClose: Boolean,
            showToday: Boolean,
        },
        optional: true,
    },
    calendarWeeks: { type: Boolean, optional: true },
    format: { type: String, optional: true },
    icons: {
        type: Object,
        shape: {
            clear: String,
            close: String,
            date: String,
            down: String,
            next: String,
            previous: String,
            time: String,
            today: String,
            up: String,
        },
        optional: true,
    },
    keyBinds: { validate: (kb) => typeof kb === "object" || kb === null, optional: true },
    locale: { type: String, optional: true },
    maxDate: { type: DateTime, optional: true },
    minDate: { type: DateTime, optional: true },
    readonly: { type: Boolean, optional: true },
    useCurrent: { type: Boolean, optional: true },
    widgetParent: { type: String, optional: true },
};
DatePicker.template = "web.DatePicker";

/**
 * Date/time picker
 *
 * Similar to the DatePicker component, adding the handling of more specific
 * time values: hour-minute-second.
 *
 * Once again, refer to the tempusdominus documentation for implementation
 * details.
 * @extends DatePicker
 */
export class DateTimePicker extends DatePicker {
    /**
     * @override
     */
    initFormat() {
        this.defaultFormat = localization.dateTimeFormat;
        this.format = formatters.get("datetime");
        this.parse = parsers.get("datetime");
        this.isLocal = true;
    }
}

DateTimePicker.defaultProps = {
    ...DatePicker.defaultProps,
    buttons: {
        showClear: false,
        showClose: true,
        showToday: false,
    },
};
