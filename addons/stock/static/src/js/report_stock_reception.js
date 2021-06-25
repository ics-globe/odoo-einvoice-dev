/** @odoo-module alias=stock.ReceptionReport **/

import clientAction from 'report.client_action';
import core from 'web.core';

const ReceptionReport = clientAction.extend({
    /**
     * @override
     */
    init: function (parent, action, options) {
        this._super.apply(this, arguments);
        this.context = action.context;
        this.pickingIds = this.context.default_picking_ids;
        this.report_name = `stock.report_reception`
        this.report_url = `/report/html/${this.report_name}/?context=${JSON.stringify(this.context)}`;
        this._title = action.name;
    },

    /**
     * @override
     */
    on_attach_callback: function () {
        this._super();
        this.iframe.addEventListener("load",
            () => this._bindAdditionalActionHandlers(),
            { once: true }
        );
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Bind additional <button> action handlers
     */
    _bindAdditionalActionHandlers: function () {
        let rr = $(this.iframe).contents().find('.o_report_reception');
        rr.on('click', '.o_report_reception_reserve', this._onClickReserve.bind(this));
        rr.on('click', '.o_report_reception_unreserve', this._onClickUnreserve.bind(this));
        rr.on('click', '.o_report_reception_forecasted', this._onClickForecastReport.bind(this));
    },


    _switchButton: function(button) {
        let $button = $(button);
        if ($button.text().indexOf("Unreserve") >= 0) {
            $button.text("Reserve");
            $button.addClass("o_report_reception_reserve");
            $button.removeClass("o_report_reception_unreserve");
        } else {
            $button.text("Unreserve");
            $button.addClass("o_report_reception_unreserve");
            $button.removeClass("o_report_reception_reserve");
        }
    },

    /**
     * Reserve the specified move(s)
     *
     * @returns {Promise}
     */
    _onClickReserve: function(ev) {
        let quantities = []  // incoming qty amounts to reserve
        let modelIds = parseInt(ev.target.getAttribute('move-id'));
        let inIds = []
        if (isNaN(modelIds)) {
            // dealing with a "Reserve All"
            $(ev.currentTarget).hide();
            modelIds = JSON.parse("[" + ev.target.getAttribute('move-ids') + "]")[0];
            let reservedIds = [];  // moves that have previously been reserved
            for (const id of modelIds) {
                let toReserve = $(this.iframe).contents().find("button.o_report_reception_reserve[move-id=" + id.toString() + "]");
                let alreadyReserved = $(this.iframe).contents().find("button.o_report_reception_unreserve[move-id=" + id.toString() + "]");
                if (toReserve.length) {
                    quantities.push(parseFloat(toReserve.attr('qty')));
                    inIds.push(JSON.parse("[" + toReserve.attr('move-ins-ids') + "]")[0]);
                    this._switchButton(toReserve);
                }
                if (alreadyReserved.length) {
                    reservedIds.push(id);
                }
            }
            if (reservedIds.length > 0) {
                modelIds = modelIds.filter(item => !reservedIds.includes(item));
            }
            if ($(ev.target).hasClass("o_reserve_all")) {
                // hide sources' "Reserve All"
                $(this.iframe).contents().find("button.o_doc_reserve_all").hide();
            }
        } else {
            quantities.push(parseFloat(ev.target.getAttribute('qty')));
            inIds = JSON.parse("[" + ev.target.getAttribute('move-ins-ids') + "]");
            this._switchButton(ev.currentTarget);
        }
        return this._rpc({
            model: 'report.stock.report_reception',
            args: [false, modelIds, quantities, inIds[0]],
            method: 'action_assign'
        })
    },

    /**
     * Unreserve the specified move
     *
     * @returns {Promise}
     */
     _onClickUnreserve: function(ev) {
        this._switchButton(ev.currentTarget);
        let quantity = parseFloat(ev.target.getAttribute('qty'));
        let modelId = parseInt(ev.target.getAttribute('move-id'));
        let inIds = JSON.parse("[" + ev.target.getAttribute('move-ins-ids') + "]");
        return this._rpc({
            model: 'report.stock.report_reception',
            args: [false, modelId, quantity, inIds[0]],
            method: 'action_unassign'
        })
    },

    /**
     * Open the forecast report for the product of
     * the selected move
     */
    _onClickForecastReport: function(ev) {
        const model = ev.target.getAttribute('model');
        const modelId = parseInt(ev.target.getAttribute('move-id'));
        return this._rpc( {
            model,
            args: [[modelId]],
            method: 'action_product_forecast_report'
        }).then((action) => {
            return this.do_action(action);
        });
    },

});

core.action_registry.add('reception_report', ReceptionReport);

export default ReceptionReport
