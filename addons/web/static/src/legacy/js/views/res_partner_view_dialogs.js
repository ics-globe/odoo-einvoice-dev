/** @odoo-module alias=web.ResPartnerFormViewDialog **/

import { _t } from 'web.core';
import Dialog from 'web.Dialog';
import { FormViewDialog } from 'web.view_dialogs';


const ResPartnerFormViewDialog = FormViewDialog.extend({

    _setRemoveButtonOption(options, btnClasses) {
        options.buttons.push({
            text: options.removeButtonText || _t("Remove"),
            classes: 'btn-secondary ' + btnClasses,
            hotkey: 'x',
            click: () =>
                this._rpc({
                    model: 'res.partner',
                    method: 'write',
                    args: [[this.res_id], {parent_id: false}],
                }).then(() => {
                    this.on('closed', this, function () {
                        this.trigger_up('reload');
                    });
                    this.close();
                })
        }, {
            title: _t('Delete'),
            icon: 'fa-trash',
            classes: 'btn-secondary ml-auto ' + btnClasses,
            hotkey: 'd',
            click: () => {
                Dialog.confirm(this, _t('Are you sure you want to delete this partner?'), {
                    confirm_callback: () => {
                        this._remove().then(this.close.bind(this));
                    },
                });
            }
        });
    },

});

export default ResPartnerFormViewDialog;
