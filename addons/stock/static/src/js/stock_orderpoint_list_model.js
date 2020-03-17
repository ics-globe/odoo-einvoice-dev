odoo.define('stock.StockOrderpointListModel', function (require) {
"use strict";

var core = require('web.core');
var ListModel = require('web.ListModel');

var qweb = core.qweb;


var StockOrderpointListModel = ListModel.extend({

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------
    /**
     */
    replenish: function (records) {
      var self = this;
      var model = records[0].model;
      var recordResIds = _.pluck(records, 'res_id');
      var context = records[0].getContext();
      return this._rpc({
          model: model,
          method: 'action_replenish',
          args: [recordResIds],
          context: context,
      }).then(function () {
          return self.do_action('stock.action_replenishment');
      });
    },

    snooze: function (records) {
      var self = this;
      var model = records[0].model;
      var recordResIds = _.pluck(records, 'res_id');
      var context = records[0].getContext();
      return this._rpc({
          model: model,
          method: 'action_snooze',
          args: [recordResIds],
          context: context,
      }).then(function () {
          return self.do_action('stock.action_replenishment');
      });
    },
});

return StockOrderpointListModel;

});
