# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import utils
from . import wizards

from odoo import api, SUPERUSER_ID


def reset_payment_provider(cr, registry, provider):
    env = api.Environment(cr, SUPERUSER_ID, {})
    providers = env['payment.provider'].search([('code', '=', provider)])
    providers.write({
        'code': 'none',
        'state': 'disabled',
    })
