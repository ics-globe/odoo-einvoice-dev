/** @odoo-module alias=purchase_requisition.PurchaseOrderLineCompareListController **/

import ListController from 'web.ListController';

const PurchaseOrderLineCompareListController = ListController.extend({

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    init: function (parent, model, renderer, params) {
        this.context = renderer.state.getContext();
        this.best_date_ids = this.context.params.best_date_ids || {};
        this.best_price_ids = this.context.params.best_price_ids || {};
        return this._super(...arguments);
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------
    /**
     * @override
     */
    _onButtonClicked: function (ev) {
        if (ev.data.attrs.class && ev.data.attrs.class.split(' ').includes('o_clear_qty_buttons')) {
            ev.stopPropagation();
            var self = this;
            return this._callButtonAction(ev.data.attrs, ev.data.record).then(() => {
                const context = this.model.localData[0] && this.model.localData[0].getContext() || {};
                return self._rpc({
                    model: "purchase.order",
                    method: 'get_tender_best_date_and_price_lines',
                    args: [self.context.active_id],
                    context: context,
                }).then((best_date_and_price) => {
                    self.renderer.best_date_ids = best_date_and_price[0] || {};
                    self.renderer.best_price_ids = best_date_and_price[1] || {};
                    self.reload();
                });
            });
        } else {
            this._super.apply(this, arguments);
        }
    },

    _onHeaderButtonClicked: function (node) {
        if (node.attrs.name && node.attrs.name === 'action_clear_quantities') {
            const self = this;
            this._super.apply(this, arguments).then(() => {
                const context = this.model.localData[0] && this.model.localData[0].getContext() || {};
                return self._rpc({
                    model: "purchase.order",
                    method: 'get_tender_best_date_and_price_lines',
                    args: [self.context.active_id],
                    context: context,
                }).then((best_date_and_price) => {
                    self.renderer.best_date_ids = best_date_and_price[0] || {};
                    self.renderer.best_price_ids = best_date_and_price[1] || {};
                    self.reload();
                });
            });
        } else {
            this._super.apply(this, arguments);
        }
    },
});

export default PurchaseOrderLineCompareListController;
