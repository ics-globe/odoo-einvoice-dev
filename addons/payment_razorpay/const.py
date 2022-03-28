# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Last updated on 26 May 2021
# https://razorpay.com/docs/payments/payments/international-payments/#supported-currencies
SUPPORTED_CURRENCIES = [
    'AED', 'ALL', 'AMD', 'ARS',
    'AUD', 'AWG', 'BBD', 'BDT',
    'BMD', 'BND', 'BOB', 'BSD',
    'BWP', 'BZD', 'CAD', 'CHF',
    'CNY', 'COP', 'CRC', 'CUP',
    'CZK', 'DKK', 'DOP', 'DZD',
    'EGP', 'ETB', 'EUR', 'FJD',
    'GBP', 'GHS', 'GIP', 'GMD',
    'GTQ', 'GYD', 'HKD', 'HNL',
    'HRK', 'HTG', 'HUF', 'IDR',
    'ILS', 'INR', 'JMD', 'KES',
    'KGS', 'KHR', 'KYD', 'KZT',
    'LAK', 'LBP', 'LKR', 'LRD',
    'LSL', 'MAD', 'MDL', 'MKD',
    'MMK', 'MNT', 'MOP', 'MUR',
    'MVR', 'MWK', 'MXN', 'MYR',
    'NAD', 'NGN', 'NIO', 'NOK',
    'NPR', 'NZD', 'PEN', 'PGK',
    'PHP', 'PKR', 'QAR', 'RUB',
    'SAR', 'SCR', 'SEK', 'SGD',
    'SLL', 'SOS', 'SSP', 'SVC',
    'SZL', 'THB', 'TTD', 'TZS',
    'USD', 'UYU', 'UZS', 'YER',
    'ZAR',
]

# Events which are handled by the webhook
HANDLED_WEBHOOK_EVENTS = [
    'subscription.charged',
]
