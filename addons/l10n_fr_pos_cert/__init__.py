# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models
from . import report
from odoo import api, SUPERUSER_ID
from odoo.addons.base.models.ir_sequence import IrSequence


def _setup_inalterability(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # enable ping for this module
    env['publisher_warranty.contract'].update_notification(cron_mode=True)

    fr_companies = env['res.company'].search([('partner_id.country_id.code', 'in', env['res.company']._get_unalterable_country())])
    if fr_companies:
        for fr_company in fr_companies:
            IrSequence._create_secure_sequence(fr_company, "l10n_fr_pos_cert_sequence_id")
