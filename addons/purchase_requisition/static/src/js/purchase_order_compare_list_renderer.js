/** @odoo-module alias=purchase_requisition.PurchaseOrderCompareListRenderer **/

import ListRenderer from 'web.ListRenderer';


const PurchaseOrderCompareListRenderer = ListRenderer.extend({
    init: function (parent, state, params) {
        this._super(...arguments);
        this.active_id = parent.res_id;
    },

    /**
     * @override
     * @private
     * @returns {Promise}
     */
     _renderRow: function (record) {
        const $tr = this._super(...arguments);
        if (this.active_id && record.res_id === this.active_id && $tr.find('o_list_record_remove')) {
            $tr.find(".o_list_record_remove").remove();
        }
        return $tr;
    }
});

export default PurchaseOrderCompareListRenderer;
