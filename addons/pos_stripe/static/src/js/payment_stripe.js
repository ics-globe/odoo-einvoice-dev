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
            console.log('Failed to discover: ', discoverResult.error);
        } else if (discoverResult.discoveredReaders.length === 0) {
            console.log('No available readers.');
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
                console.log('Failed to disconnect: ', disconnectResult.error);
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
                this.terminal.connectReader(selectedReader).then(function(connectResult) {
                    if (connectResult.error) {
                    console.log('Failed to connect: ', connectResult.error);
                    reject();
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
            console.log('result: ', result.error);
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
        console.log('send_payment_request');
        var self = this;
        var line = this.pos.get_order().selected_paymentline;
        line.set_payment_status('pending');
        var connected_reader = new Promise(function(resolve, reject) {
            self.checkReader(resolve, reject);
        });
        connected_reader.finally(function () {
                self.collect_payment(self.pos.currency.name, line.amount);
            });
        //this.collect_payment(this.pos.currency.name, line.amount);

/*        this.discoverReaders();
        
        this._super.apply(this, arguments);
        this._reset_state();
        return this._stripe_pay();*/
    },

    send_payment_cancel: function (order, cid) {
        this._super.apply(this, arguments);
        // set only if we are polling
        this.was_cancelled = !!this.polling;
        return this._stripe_cancel();
    },

    close: function () {
        this._super.apply(this, arguments);
    },

    // private methods

    _handle_odoo_connection_failure: function (data) {
        // handle timeout
        var line = this.pos.get_order().selected_paymentline;
        if (line) {
            line.set_payment_status('retry');
        }
        this._show_error(_t('Could not connect to the Odoo server, please check your internet connection and try again.'));

        return Promise.reject(data); // prevent subsequent onFullFilled's from being called
    },

    _call_stripe: function (data, operation) {
        return rpc.query({
            model: 'pos.payment.method',
            method: 'proxy_stripe_request',
            args: [[this.payment_method.id], data, operation],
        }, {
            // When a payment terminal is disconnected it takes Adyen
            // a while to return an error (~6s). So wait 10 seconds
            // before concluding Odoo is unreachable.
            timeout: 10000,
            shadow: true,
        }).catch(this._handle_odoo_connection_failure.bind(this));
    },

    _stripe_get_sale_id: function () {
        var config = this.pos.config;
        return _.str.sprintf('%s (ID: %s)', config.display_name, config.id);
    },

    _stripe_pay: function () {
        var self = this;
        var order = this.pos.get_order();

        if (order.selected_paymentline.amount < 0) {
            this._show_error(_t('Cannot process transactions with negative amount.'));
            return Promise.resolve();
        }

        if (order === this.poll_error_order) {
            delete this.poll_error_order;
            return self._stripe_handle_response({});
        }

        var data = this._stripe_pay_data();

        return this._call_stripe(data).then(function (data) {
            return self._stripe_handle_response(data);
        });
    },

    _stripe_cancel: function (ignore_error) {
        var self = this;
        var previous_service_id = this.most_recent_service_id;
        var header = _.extend(this._stripe_common_message_header(), {
            'MessageCategory': 'Abort',
        });

        var data = {
            'SaleToPOIRequest': {
                'MessageHeader': header,
                'AbortRequest': {
                    'AbortReason': 'MerchantAbort',
                    'MessageReference': {
                        'MessageCategory': 'Payment',
                        'ServiceID': previous_service_id,
                    }
                },
            }
        };

        return this._call_stripe(data).then(function (data) {

            // Only valid response is a 200 OK HTTP response which is
            // represented by true.
            if (! ignore_error && data !== "ok") {
                self._show_error(_t('Cancelling the payment failed. Please cancel it manually on the payment terminal.'));
            }
        });
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

    _poll_for_response: function (resolve, reject) {
        var self = this;
        if (this.was_cancelled) {
            resolve(false);
            return Promise.resolve();
        }

        return rpc.query({
            model: 'pos.payment.method',
            method: 'get_latest_stripe_status',
            args: [[this.payment_method.id], this._stripe_get_sale_id()],
        }, {
            timeout: 5000,
            shadow: true,
        }).catch(function (data) {
            if (self.remaining_polls != 0) {
                self.remaining_polls--;
            } else {
                reject();
                self.poll_error_order = self.pos.get_order();
                return self._handle_odoo_connection_failure(data);
            }
            // This is to make sure that if 'data' is not an instance of Error (i.e. timeout error),
            // this promise don't resolve -- that is, it doesn't go to the 'then' clause.
            return Promise.reject(data);
        }).then(function (status) {
            var notification = status.latest_response;
            var last_diagnosis_service_id = status.last_received_diagnosis_id;
            var order = self.pos.get_order();
            var line = order.selected_paymentline;


            if (self.last_diagnosis_service_id != last_diagnosis_service_id) {
                self.last_diagnosis_service_id = last_diagnosis_service_id;
                self.remaining_polls = 2;
            } else {
                self.remaining_polls--;
            }

            if (notification && notification.SaleToPOIResponse.MessageHeader.ServiceID == self.most_recent_service_id) {
                var response = notification.SaleToPOIResponse.PaymentResponse.Response;
                var additional_response = new URLSearchParams(response.AdditionalResponse);

                if (response.Result == 'Success') {
                    var config = self.pos.config;
                    var payment_response = notification.SaleToPOIResponse.PaymentResponse;
                    var payment_result = payment_response.PaymentResult;

                    var cashier_receipt = payment_response.PaymentReceipt.find(function (receipt) {
                        return receipt.DocumentQualifier == 'CashierReceipt';
                    });

                    if (cashier_receipt) {
                        line.set_cashier_receipt(self._convert_receipt_info(cashier_receipt.OutputContent.OutputText));
                    }

                    var customer_receipt = payment_response.PaymentReceipt.find(function (receipt) {
                        return receipt.DocumentQualifier == 'CustomerReceipt';
                    });

                    if (customer_receipt) {
                        line.set_receipt_info(self._convert_receipt_info(customer_receipt.OutputContent.OutputText));
                    }

                    var tip_amount = payment_result.AmountsResp.TipAmount;
                    if (config.stripe_ask_customer_for_tip && tip_amount > 0) {
                        order.set_tip(tip_amount);
                        line.set_amount(payment_result.AmountsResp.AuthorizedAmount);
                    }

                    line.transaction_id = additional_response.get('pspReference');
                    line.card_type = additional_response.get('cardType');
                    line.cardholder_name = additional_response.get('cardHolderName') || '';
                    resolve(true);
                } else {
                    var message = additional_response.get('message');
                    self._show_error(_.str.sprintf(_t('Message from Adyen: %s'), message));

                    // this means the transaction was cancelled by pressing the cancel button on the device
                    if (message.startsWith('108 ')) {
                        resolve(false);
                    } else {
                        line.set_payment_status('retry');
                        reject();
                    }
                }
            } else if (self.remaining_polls <= 0) {
                self._show_error(_t('The connection to your payment terminal failed. Please check if it is still connected to the internet.'));
                self._stripe_cancel();
                resolve(false);
            }
        });
    },

    _stripe_handle_response: function (response) {
        var line = this.pos.get_order().selected_paymentline;

        if (response.error && response.error.status_code == 401) {
            this._show_error(_t('Authentication failed. Please check your Adyen credentials.'));
            line.set_payment_status('force_done');
            return Promise.resolve();
        }

        response = response.SaleToPOIRequest;
        if (response && response.EventNotification && response.EventNotification.EventToNotify == 'Reject') {
            console.error('error from Adyen', response);

            var msg = '';
            if (response.EventNotification) {
                var params = new URLSearchParams(response.EventNotification.EventDetails);
                msg = params.get('message');
            }

            this._show_error(_.str.sprintf(_t('An unexpected error occurred. Message from Adyen: %s'), msg));
            if (line) {
                line.set_payment_status('force_done');
            }

            return Promise.resolve();
        } else {
            line.set_payment_status('waitingCard');

            var self = this;
            var res = new Promise(function (resolve, reject) {
                // clear previous intervals just in case, otherwise
                // it'll run forever
                clearTimeout(self.polling);

                self.polling = setInterval(function () {
                    self._poll_for_response(resolve, reject);
                }, 5500);
            });

            // make sure to stop polling when we're done
            res.finally(function () {
                self._reset_state();
            });

            return res;
        }
    },

    _show_error: function (msg, title) {
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
