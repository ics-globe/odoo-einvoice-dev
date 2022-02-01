odoo.define('point_of_sale.AlertPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { _lt } = require('@web/core/l10n/translation');

    class AlertPopup extends AbstractAwaitablePopup {}
    AlertPopup.template = 'AlertPopup';
    AlertPopup.defaultProps = {
        confirmText: _lt('Ok'),
        title: _lt('Alert'),
        body: '',
    };

    Registries.Component.add(AlertPopup);

    return AlertPopup;
});
