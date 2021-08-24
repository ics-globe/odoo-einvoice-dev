odoo.define('point_of_sale.many2one_placeholder', function (require) {
    'use strict;';

    const relationalFields = require('web.relational_fields');
    const FieldMany2One = relationalFields.FieldMany2One;
    const FieldRegistry = require('web.field_registry');

    const FieldMany2OnePlaceholder = FieldMany2One.extend({
        init: function () {
            this._super(...arguments);
            if (this.mode == 'edit') {
                let computedPlaceholder;
                const placeholderField = this.attrs['placeholder-field'];
                if (placeholderField && placeholderField in this.record.data) {
                    const val = this.record.data[placeholderField];
                    if (val.type == 'record') {
                        computedPlaceholder = val.data.display_name;
                    } else {
                        computedPlaceholder = val;
                    }
                }
                this.attrs.placeholder = computedPlaceholder || this.attrs.placeholder;
            }
        },
    });

    FieldRegistry.add('many2one_placeholder', FieldMany2OnePlaceholder);
    return FieldMany2OnePlaceholder;
});
