odoo.define('hr_holidays/static/src/models/partner/partner.js', function (require) {
'use strict';

const { and, branching, dateToLocaleDateString, fieldValue, isFieldDefined, localeFromUnderscoreToDash, sprintf, stringToDate } = require('@mail/model/model_compute_method');
const {
    registerClassPatchModel,
    registerFieldPatchModel,
    registerInstancePatchModel,
} = require('@mail/model/model_core');
const { attr } = require('@mail/model/model_field');
const { clear } = require('@mail/model/model_field_command');

const { _lt } = require('@web/core/l10n/translation');

registerClassPatchModel('mail.partner', 'hr_holidays/static/src/models/partner/partner.js', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('out_of_office_date_end' in data) {
            data2.outOfOfficeDateEnd = data.out_of_office_date_end ? data.out_of_office_date_end : clear();
        }
        return data2;
    },
});

registerInstancePatchModel('mail.partner', 'hr_holidays/static/src/models/partner/partner.js', {
    /**
     * @override
     */
    _computeIsOnline() {
        if (['leave_online', 'leave_away'].includes(this.im_status)) {
            return true;
        }
        return this._super();
    },
});

registerFieldPatchModel('mail.partner', 'hr/static/src/models/partner/partner.js', {
    /**
     * Date of end of the out of office period of the partner as string.
     * String is expected to use Odoo's date string format
     * (examples: '2011-12-01' or '2011-12-01').
     */
    outOfOfficeDateEnd: attr(),
    /**
     * Text shown when partner is out of office.
     */
    outOfOfficeText: attr({
        compute: branching(
            and(
                isFieldDefined('outOfOfficeDateEnd'),
                isFieldDefined('messaging.locale.language'),
            ),
            sprintf(
                _lt("Out of office until %s"),
                dateToLocaleDateString(
                    stringToDate(fieldValue('outOfOfficeDateEnd')),
                    localeFromUnderscoreToDash(fieldValue('messaging.locale.language')),
                ),
            ),
            clear(),
        ),
    }),
});

});
