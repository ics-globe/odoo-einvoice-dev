# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple

API_VERSION = '2019-05-16'  # The API version of Stripe implemented in this module

# Stripe proxy URL
PROXY_URL = 'https://stripe.api.odoo.com/api/stripe/'

# Support payment method types
PMT = namedtuple('PaymentMethodType', ['name', 'countries', 'currencies', 'recurrence'])
PAYMENT_METHOD_TYPES = [
    PMT('card', [], [], 'recurring'),
    PMT('ideal', ['nl'], ['eur'], 'punctual'),
    PMT('bancontact', ['be'], ['eur'], 'punctual'),
    PMT('eps', ['at'], ['eur'], 'punctual'),
    PMT('giropay', ['de'], ['eur'], 'punctual'),
    PMT('p24', ['pl'], ['eur', 'pln'], 'punctual'),
]

# Mapping of transaction states to Stripe {Payment,Setup}Intent statuses.
# See https://stripe.com/docs/payments/intents#intent-statuses for the exhaustive list of status.
INTENT_STATUS_MAPPING = {
    'draft': ('requires_payment_method', 'requires_confirmation', 'requires_action'),
    'pending': ('processing',),
    'authorized': ('requires_capture',),
    'done': ('succeeded',),
    'cancel': ('canceled',),
}

# Events which are handled by the webhook
HANDLED_WEBHOOK_EVENTS = [
    'payment_intent.amount_capturable_updated',
    'payment_intent.succeeded',
    'setup_intent.succeeded',
]

# Countries supported by stripe
# This set is sorted and taken from https://stripe.com/global page
STRIPE_SUPPORTED_COUNTRIES = {
    'AE',
    'AT',
    'AU',
    'BE',
    'BG',
    'BR',
    'CA',
    'CH',
    'CY',
    'CZ',
    'DE',
    'DK',
    'EE',
    'ES',
    'FI',
    'FR',
    'GB',
    'GI',  # Beta
    'GR',
    'HK',
    'HR',  # Beta
    'HU',
    'ID',  # Beta
    'IE',
    'IT',
    'JP',
    'LI',  # Beta
    'LT',
    'LU',
    'LV',
    'MT',
    'MX',
    'MY',
    'NL',
    'NO',
    'NZ',
    'PH',  # Beta
    'PL',
    'PT',
    'RO',
    'SE',
    'SG',
    'SI',
    'SK',
    'TH',  # Beta
    'US',
}
