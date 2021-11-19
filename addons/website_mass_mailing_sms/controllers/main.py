# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.mass_mailing.controllers import main


class MassMailController(main.MassMailController):

    def set_default_input_value(self, input_name):
        value = super(MassMailController, self).set_default_input_value(input_name)
        if not value and input_name == 'mobile':
            if not request.env.user._is_public():
                value = request.env.user.partner_id.mobile
            elif request.session.get('mass_mailing_mobile'):
                value = request.session['mass_mailing_mobile']
        return value
