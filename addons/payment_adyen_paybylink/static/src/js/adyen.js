odoo.define('payment_adyen_paybylink.adyen', function (require) {
    "use strict";

    var core = require('web.core');

    var _t = core._t;

    if ($.blockUI) {
        // our message needs to appear above the modal dialog
        $.blockUI.defaults.baseZ = 2147483647; //same z-index as StripeCheckout
        $.blockUI.defaults.css.border = '0';
        $.blockUI.defaults.css["background-color"] = '';
        $.blockUI.defaults.overlayCSS["opacity"] = '0.9';
    }

    require('web.dom_ready');
    if (!$('.o_payment_form').length) {
        return Promise.reject("DOM doesn't contain '.o_payment_form'");
    }

    var observer = new MutationObserver(function (mutations, observer) {
        for (var i = 0; i < mutations.length; ++i) {
            for (var j = 0; j < mutations[i].addedNodes.length; ++j) {
                if (mutations[i].addedNodes[j].tagName.toLowerCase() === "form" && mutations[i].addedNodes[j].getAttribute('provider') === 'adyen') {
                    _redirectToAdyenCheckout($(mutations[i].addedNodes[j]));
                }
            }
        }
    });

    function _redirectToAdyenCheckout(providerForm) {
        // Open Checkout with further options
        if ($.blockUI) {
            var msg = _t("Just one more second, We are redirecting you to Adyen...");
            $.blockUI({
                'message': '<h2 class="text-white"><img src="/web/static/src/img/spin.png" class="fa-pulse"/>' +
                        '    <br />' + msg +
                        '</h2>'
            });
        }

        var _getAdyenInputValue = function (name) {
            return providerForm.find('input[name="' + name + '"]').val();
        };

        var paymentForm = $('.o_payment_form');
        if (!paymentForm.find('i').length) {
            paymentForm.append('<i class="fa fa-spinner fa-spin"/>');
            paymentForm.attr('disabled', 'disabled');
        }

        console.log(_getAdyenInputValue('adyen_url'))
        window.location.href = _getAdyenInputValue('adyen_link')
    }

    observer.observe(document.body, {childList: true});
    _redirectToAdyenCheckout($('form[provider="adyen"]'));

});
