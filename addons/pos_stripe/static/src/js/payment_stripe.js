odoo.define('pos_stripe.payment', function (require) {
"use strict";

var core = require('web.core');
var rpc = require('web.rpc');
var PaymentInterface = require('point_of_sale.PaymentInterface');
const { Gui } = require('point_of_sale.Gui');

var _t = core._t;

function StripeunexpectedDisconnect() {
  // In this function, your app should notify the user that the reader disconnected.
  // You can also include a way to attempt to reconnect to a reader.
  console.log("Disconnected from reader")
}

function StripefetchConnectionToken() {
    // Do not cache or hardcode the ConnectionToken.
    return rpc.query({
        model: 'pos.payment.method',
        method: 'stripe_connection_token',
    }, {
        silent: true,
    }).catch(function (error) {
        this._show_error(_t('error'));
    }).then(function (data) {
        console.log(data);
        return data.secret;
    });
}

var PaymentStripe = PaymentInterface.extend({
    init: function (pos, payment_method) {
        this._super(...arguments);
        this.terminal = StripeTerminal.create({
          onFetchConnectionToken: StripefetchConnectionToken,
          onUnexpectedReaderDisconnect: StripeunexpectedDisconnect,
        });
        this.discoverReaders();
    },

    discoverReaders() {
      /*const config = {location: 'tml_EhVtrQrEskfIlX'};*/
      const config = {};
      var self = this;

    this.terminal.discoverReaders(config).then(function(discoverResult) {
        if (discoverResult.error) {
            self._show_error(_.str.sprintf(_t('Failed to discover: %s'), discoverResult.error));
            return Promise.resolve();
        } else if (discoverResult.discoveredReaders.length === 0) {
            self._show_error(_t('No available Stripe readers.'));
            return Promise.resolve();
        } else {
            // You should show the list of discoveredReaders to the
            // cashier here and let them select which to connect to (see below).
            //self.connectReader(discoverResult);
            self.pos.discoveredReaders = JSON.stringify(discoverResult.discoveredReaders);
            // Need to stringify all Readers to avoid to put the array into a proxy Object not interpretable
            // for the Stripe SDK
            console.log(discoverResult);
        }
        });
    },

    checkReader(resolve, reject) {
        var self = this;
        console.log('connectReader');
        console.log(this.terminal.getConnectionStatus());
        console.log(self.pos.connectedReader);
        console.log(this.payment_method.stripe_serial_number);
        // Because the reader can only connect to one instance of the SDK at a time.
        // We need the disconnect this reader if we want to use another one
        if (
            self.pos.connectedReader != this.payment_method.stripe_serial_number &&
            this.terminal.getConnectionStatus() == 'connected'
            ) {
            this.terminal.disconnectReader().then(function(disconnectResult) {
                if (disconnectResult.error) {
                self._show_error(disconnectResult.error.message, disconnectResult.error.code);
                return Promise.resolve();
                reject();
                } else {
                console.log('Disconnected to reader ');
                self.connectReader(resolve, reject);
                }
            });
        } else if (this.terminal.getConnectionStatus() == 'not_connected') {
            self.connectReader(resolve, reject);
        } else {resolve();}
    },

    connectReader(resolve, reject) {
        var self = this;
        var discoveredReaders = JSON.parse(this.pos.discoveredReaders);
        for (const selectedReader of discoveredReaders) {
            if (selectedReader.serial_number == this.payment_method.stripe_serial_number) {
                this.terminal.connectReader(selectedReader, {fail_if_in_use: true}).then(function(connectResult) {
                    if (connectResult.error) {
                    self._show_error(connectResult.error.message, connectResult.error.code);
                    resolve(false);
                    } else {
                    console.log('Connected to reader: ', connectResult.reader.label);
                    self.pos.connectedReader = self.payment_method.stripe_serial_number;
                    resolve();
                    }
                });
            }
        }
    },

    collect_payment(currency, amount) {
        var self = this;
        var line = this.pos.get_order().selected_paymentline;
        this.fetch_payment_intent_client_secret(currency, amount).then(function(client_secret) {
            console.log('client_secret');
            console.log(client_secret);
          self.terminal.collectPaymentMethod(client_secret).then(function(result) {
          if (result.error) {
            self._show_error(result.error.message, result.error.code);
            return Promise.resolve();
          } else {
              console.log('terminal.collectPaymentMethod', result.paymentIntent);
              self.terminal.processPayment(result.paymentIntent).then(function(result) {
              if (result.error) {
                console.log(result.error);
              } else if (result.paymentIntent) {
                  var paymentIntentId = result.paymentIntent.id;
                  console.log('terminal.processPayment', result.paymentIntent);
                  self.capture_payment(result.paymentIntent.id).then(function(result) {
                    console.log('result');
                    console.log(result);
                    console.log(line);
                    line.set_payment_status('done');
                    line.transaction_id = ('test1');
                    line.card_type = ('test2');
                    line.cardholder_name = ('test3');
                    line.set_receipt_info('test4');
                    line.set_cashier_receipt('test5');
                    console.log(line);
                    return resolve();
                  });
              }
            });
          }
        });
      });
    },

    capture_payment(paymentIntentId) {
        return rpc.query({
            model: 'pos.payment.method',
            method: 'stripe_capture_payment',
            args: [paymentIntentId],
        }, {
            silent: true,
        }).catch(function (error) {
            this._show_error(_t('error'));
        }).then(function (data) {
            console.log(data);
            return data;
        });
    },

    fetch_payment_intent_client_secret(currency, amount) {
        return rpc.query({
            model: 'pos.payment.method',
            method: 'stripe_payment_intent',
            args: [currency, amount],
        }, {
            silent: true,
        }).catch(function (error) {
            this._show_error(_t('error'));
        }).then(function (data) {
            console.log(data);
            return data.client_secret;
        });
    },

    send_payment_request: function (cid) {
        this._super.apply(this, arguments);
        console.log('send_payment_request');
        var self = this;
        var line = this.pos.get_order().selected_paymentline;

        var connected_reader = new Promise(function(resolve, reject) {
            self.checkReader(resolve, reject);
        });
        return connected_reader.finally(function () {
                self.collect_payment(self.pos.currency.name, line.amount);
            });
    },

    send_payment_cancel: function (order, cid) {
        this._super.apply(this, arguments);
        return this.stripe_cancel();
    },

    close: function () {
        this._super.apply(this, arguments);
    },

    // private methods

/*    _handle_odoo_connection_failure: function (data) {
        // handle timeout
        var line = this.pos.get_order().selected_paymentline;
        if (line) {
            line.set_payment_status('retry');
        }
        this._show_error(_t('Could not connect to the Odoo server, please check your internet connection and try again.'));

        return Promise.reject(data); // prevent subsequent onFullFilled's from being called
    },*/

    _stripe_get_sale_id: function () {
        var config = this.pos.config;
        return _.str.sprintf('%s (ID: %s)', config.display_name, config.id);
    },

    _get_connection_status(resolve, reject) {
        var self = this;
        var connection_status = this.terminal.getConnectionStatus();
        if (connection_status == 'not_connected') {
            resolve();
        } else {
            self._show_error(_t('Payment can not be canceled because not reader connected'));
            reject();
        }
    },

    stripe_cancel() {
        var self = this;
        var connection_status = new Promise(function(resolve, reject) {
            self._get_connection_status(resolve, reject);
        });
        return connection_status.finally();


/*        if (this.terminal.getConnectionStatus() == 'not_connected') {
            return Promise.resolve(true);
        }*/
/*         else {
            return this.terminal.cancelCollectPaymentMethod();
        }*/
/*            .then(function(result) {
                if (result) {
                    console.log('cancel error');
                    console.log(result);
                } else {
                    console.log('cancle true');
                    console.log(result);
                }
            })
            .catch(function(result) {
                if (result) {
                    console.log('cancel error');
                    console.log(result);
                } else {
                    console.log('cancle true');
                    console.log(result);
                }
            });*/
    },

    _convert_receipt_info: function (output_text) {
        return output_text.reduce(function (acc, entry) {
            var params = new URLSearchParams(entry.Text);

            if (params.get('name') && !params.get('value')) {
                return acc + _.str.sprintf('<br/>%s', params.get('name'));
            } else if (params.get('name') && params.get('value')) {
                return acc + _.str.sprintf('<br/>%s: %s', params.get('name'), params.get('value'));
            }

            return acc;
        }, '');
    },

    _show_error(msg, title) {
        if (!title) {
            title =  _t('Stripe Error');
        }
        Gui.showPopup('ErrorPopup',{
            'title': title,
            'body': msg,
        });
    },
});

return PaymentStripe;
});
