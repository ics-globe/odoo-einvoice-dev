
import json
import logging
import pprint

import requests

_logger = logging.getLogger(__name__)

class MercadoPagoAPI:

    def __init__(self, acquirer):
        self._url = "https://api.mercadopago.com"

        self._state = acquirer.state

        self._public_key = acquirer.mercado_pago_public_key
        self._private_key = acquirer.mercado_pago_private_key

    def _make_request(self, endpoint, method, data=None):

        request_methods = {
            "post": requests.post,
            "get": requests.get,
            "put": requests.put,
            "delete": requests.delete,
        }

        headers = {
            'Authorization': f"Bearer {self._private_key}",
            'Content-Type': 'application/json'
        }

        request_url = self._url + endpoint

        _logger.info("sending request to %s:\n%s\n%s", request_url, pprint.pformat(headers),
                     pprint.pformat(data or {}))
        response = (request_methods[method])(request_url, data=json.dumps(data), headers=headers,
                                             timeout=60)
        response.raise_for_status()
        response = json.loads(response.content)
        _logger.info("response received:\n%s", pprint.pformat(response))

        if "error" in response and response["error"]:
            err_msg = "\n".join(cause["description"] for cause in response["cause"])
            return {
                "err_code": response["cause"][0]["code"],
                "err_msg": err_msg,
            }

        return response

    def create_payment(self, description, installments, issuer_id, order, payer, payment_method_id,
                        transaction_amount, additional_info=None, binary_mode=False, capture=True,
                       **kwargs):

        data = {
            "binary_mode": str(binary_mode),
            "capture": str(capture),
            "description": description,
            "installments": installments,
            "issuer_id": issuer_id,
            "order": order,
            "payer": payer,
            "payment_method_id": payment_method_id,
            "transaction_amount": transaction_amount,
            **kwargs
        }

        response = self._make_request("/v1/payments", "post", data)

    def search_payments(self, sort_field, criteria, external_reference):

        data = {
            "sort": sort_field,
            "criteria": criteria,
            "external_reference": external_reference,
        }

        response = self._make_request("/v1/payments/search", "get", data)

    def get_payment(self, payment_id):
        response = self._make_request(f"/v1/payments/{payment_id}", "get")

    def update_payment(self, payment_id, status, transaction_amount, capture=True, **kwargs):

        data = {
            "status": status,
            "transaction_amount": transaction_amount,
            "capture": str(capture),
            **kwargs
        }

        response = self._make_request(f"/v1/payments/{payment_id}", "put", data)

    def get_payment_methods(self):
        response = self._make_request("v1/payment_methods", "get")

    def create_customer(self, partner, default_card="None", **kwargs):

        data = {
            "email": partner.email or "",
            "default_card": default_card,
            "first_name": partner.name.split(" ")[0],
            "last_name": partner.name.split(" ")[1] if len(partner.name.split(" "))>=2 else "",
            "phone": {
                "area_code": "",
                "number": partner.phone or "",
            },
            **kwargs,
        }

        response = self._make_request("/v1/customers", "post")

    def search_customers(self, email):
        response = self._make_request("/v1/customers/search", {"email": email})

    def get_customer(self, customer_id):
        response = self._make_request(f"/v1/customers/{customer_id}")

    def update_customer(self, customer_id, **kwargs):
       response = self._make_request(f"/v1/customers/{customer_id}", data=kwargs)

    def create_refresh_token(self, client_id, client_secret, grant_type, **kwargs):

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": grant_type,
            **kwargs
        }

        response = self._make_request("oauth/token", "post", data)

    def create_order(self, payer, site_id, external_reference, **kwargs):

      data = {
          "payer": payer,
          "site_id": site_id,
          "external_reference": external_reference,
          **kwargs
      }

      response = self._make_request("/merchant_orders", "post", data)

    def search_orders(self):
        response = self._make_request("/merchant_orders/search", "get")

    def get_order(self, order_id):
        response = self._make_request(f"/merchant_orders/{order_id}", "get")

    def update_order(self, order_id, **kwargs):
        response = self._make_request(f"/merchant_orders/{order_id}", "put", data=kwargs)

    def create_preference(self, auto_return, back_urls, external_reference, payer, **kwargs):

        data = {
            "auto_return": auto_return,
            "back_urls": back_urls,
            "external_reference": external_reference,
            "payer": payer,
            **kwargs
        }

        response = self._make_request("/checkout/preferences", "post", data)

    def search_preferences(self):
        response = self._make_request("/checkout/preferences/search", "get")

    def get_preference(self, preference_id):
        response = self._make_reques(f"/checkout/preferences/{preference_id}", "get")

    def update_preference(self, preference_id, **kwargs):
        response = self._make_request(f"/checkout/preferences/{preference_id}", "get", data=kwargs)

    def create_refund(self, payment_id, amount=None, idempotency_key=None):

        data = {}
        if amount is not None:
            data["amount"] = amount
        if idempotency_key is not None:
            data["X-idempotency-key"] = idempotency_key

        response = self._make_request(f"/v1/payments/{payment_id}/refunds", "post", data)

    def get_chargeback(self, chargeback_id):
        response = self._make_request(f"/v1/chargebacks/{chargeback_id}", "get")

    def get_refund_list(self, payment_id):
        response = self._make_request(f"/v1/payments{payment_id}/refunds", "get")

    def get_refund(self, payment_id, refund_id):
        response = self._make_request(f"/v1/payments{payment_id}/refunds/{refund_id}", "get")

    def save_card(self, customer_id, token):
        response = self._make_request(f"/v1/customers/{customer_id}/cards", "post",
                                      data={"token": token})

    def get_customer_cards(self, customer_id):
        response = self._make_request(f"/v1/customers/{customer_id}/cards", "get")

    def get_card(self, customer_id, card_id):
        response = self._make_request(f"/v1/customers/{customer_id}/cards/{card_id}", "get")

    def update_card(self, customer_id, card_id, token):
        response = self._make_request(f"/v1/customers/{customer_id}/cards/{card_id}", "put",
                                      data={"token": token})

    def delete_card(self, customer_id, card_id):
        response = self._make_request(f"/v1/customers/{customer_id}/cards/{card_id}", "delete")

    def get_document_types(self):
        response = self._make_request("/v1/identification_types", "get")

    def create_subscription(self, auto_recurring, collector_id, external_reference, **kwargs):

        data = {
            "auto_recurring": auto_recurring,
            "collector_id": collector_id,
            "external_reference": external_reference,
            **kwargs
        }

        response = self._make_request("/preapproval", "post", data)
