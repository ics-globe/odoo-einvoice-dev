/** @odoo-module **/

/**
 * Provides built-in compute methods that can be defined in a simple way and
 * that are executable by the model manager. Each param of each compute method
 * can always be either a final value, or another compute method returning this
 * value when executed.
 */
export class ComputeMethod {
    /**
     * @constructor
     * @param {string} name - method name
     * @param {any} [value] - value(s) used for the method
     */
    constructor(name, value) {
        this.name = name;
        this.value = value;
    }
}

/**
 * Compute method that returns true if all the given arguments are also true.
 *
 * @param {Array<boolean|ComputeMethod>|ComputeMethod} list
 * @returns {ComputeMethod}
 */
export function and(...list) {
    return new ComputeMethod('and', list);
}

/**
 * Compute method that returns whether all the given arguments are defined and
 * equal to each other.
 *
 * @param {Array<any|ComputeMethod>|ComputeMethod} list
 * @returns {ComputeMethod}
 */
export function areFieldsDefinedAndEqual(...list) {
    return new ComputeMethod('areFieldsDefinedAndEqual', list);
}

/**
 * Compute method that returns the positive value if the condition is true and
 * returns the negative value otherwise.
 *
 * @param {boolean|ComputeMethod} condition
 * @param {any|ComputeMethod} positive
 * @param {any|ComputeMethod} negative
 * @returns {ComputeMethod}
 */
export function branching(condition, positive, negative) {
    return new ComputeMethod('branching', [condition, positive, negative]);
}

/**
 * Compute method that returns the clear field command if the condition is true.
 *
 * @param {boolean|ComputeMethod} condition
 * @returns {ComputeMethod}
 */
export function clearIfTrue(condition) {
    return new ComputeMethod('clearIfTrue', condition);
}

/**
 * Compute method that returns a localized string based on the given date object
 * and a localeCode.
 *
 * @param {Date|ComputeMethod} date
 * @param {string|ComputeMethod} localeCode
 * @returns {ComputeMethod}
 */
export function dateToLocaleDateString(date, localeCode) {
    return new ComputeMethod('dateToLocaleDateString', [date, localeCode]);
}

/**
 * Compute method that follows relation(s). The argument is the name of a field,
 * starting from the model on which the compute is defined, and optionally
 * following relations with dot notation. When following relations, the path is
 * considered undefined as soon as one relation is undefined. Following multiple
 * x2many relations flattens the result.
 *
 * @param {string|ComputeMethod} fieldPath
 * @returns {ComputeMethod}
 */
export function fieldValue(fieldPath) {
    return new ComputeMethod('fieldValue', fieldPath);
}

/**
 * Compute method that returns the mapped value of first defined field in the
 * list.
 *
 * @param {Array<Array<string|ComputeMethod>|ComputeMethod>|ComputeMethod} list
 * @returns {ComputeMethod}
 */
export function firstDefinedFieldMapping(...list) {
    return new ComputeMethod('firstDefinedFieldMapping', list);
}

/**
 * Compute method that returns the first defined argument among a list of
 * arguments.
 *
 * @param {Array<any|ComputeMethod>|ComputeMethod} list
 * @returns {ComputeMethod}
 */
export function firstDefinedFieldValue(...list) {
    return new ComputeMethod('firstDefinedFieldValue', list);
}

/**
 * Compute method that returns true if any of the given field is true.
 *
 * @param {Array<string|ComputeMethod>|ComputeMethod} list
 * @returns {ComputeMethod}
 */
export function isAnyFieldTrue(...list) {
    return new ComputeMethod('isAnyFieldTrue', list);
}

/**
 * Compute method that returns true if the given value is defined.
 *
 * @param {any|ComputeMethod} value
 * @returns {ComputeMethod}
 */
export function isDefined(value) {
    return new ComputeMethod('isDefined', value);
}

/**
 * Compute method that returns true if the given fieldPath is defined.
 *
 * @param {string|ComputeMethod} fieldPath
 * @returns {ComputeMethod}
 */
export function isFieldDefined(fieldPath) {
    return new ComputeMethod('isFieldDefined', fieldPath);
}

/**
 * Compute method that returns true if the given fieldPath is defined and equal
 * to any of the values.
 *
 * @param {string|ComputeMethod} fieldPath
 * @param {Array<any|ComputeMethod>|ComputeMethod} values
 * @returns {ComputeMethod}
 */
export function isFieldDefinedAndEqualToAnyOf(fieldPath, values) {
    return new ComputeMethod('isFieldDefinedAndEqualToAnyOf', [fieldPath, values]);
}

/**
 * Compute method that returns true if the given fieldPath is defined and
 * includes the given value.
 *
 * @param {string|ComputeMethod} fieldPath
 * @param {any|ComputeMethod} value
 * @returns {ComputeMethod}
 */
export function isFieldDefinedAndIncluding(fieldPath, value) {
    return new ComputeMethod('isFieldDefinedAndIncluding', [fieldPath, value]);
}

/**
 * Compute method that returns a locale string with a dash from a locale string
 * with an underscore.
 *
 * @param {string|ComputeMethod} localeString
 * @returns {string}
 */
export function localeFromUnderscoreToDash(localeString) {
    return new ComputeMethod('localeFromUnderscoreToDash', localeString);
}

/**
 * Compute method that returns true if any of the given arguments is true.
 *
 * @param {Array<boolean|ComputeMethod>|ComputeMethod} list
 * @returns {ComputeMethod}
 */
export function or(...list) {
    return new ComputeMethod('or', list);
}

/**
 * Compute method that returns a replace field command of which the record(s)
 * are provided (or a clear field command if no record is provided).
 *
 * @param {mail.model|Array<mail.model|ComputeMethod>|ComputeMethod} records
 * @returns {ComputeMethod}
 */
export function replaceOrClear(records) {
    return new ComputeMethod('replaceOrClear', records);
}

/**
 * Compute method that returns the clear field command if the value is not
 * defined.
 *
 * @param {any|ComputeMethod} value
 * @returns {ComputeMethod}
 */
export function setOrClear(value) {
    return new ComputeMethod('setOrClear', value);
}

/**
 * Compute method that returns the given placeholderString with the placeholders
 * replaced by the given arguments.
 *
 * @param {string|computeMethod} placeholderString
 * @param {Array<string|ComputeMethod>} args
 * @returns {ComputeMethod}
 */
export function sprintf(placeholderString, ...args) {
    return new ComputeMethod('sprintf', [placeholderString, args]);
}

/**
 * Compute method that returns a date Object from a given dateString.
 *
 * @param {string|ComputeMethod>} dateString
 * @returns {ComputeMethod}
 */
export function stringToDate(dateString) {
    return new ComputeMethod('stringToDate', dateString);
}
