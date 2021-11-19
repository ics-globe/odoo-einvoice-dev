# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _
from odoo.http import request
from odoo.addons.website.controllers.form import WebsiteForm
from odoo.exceptions import ValidationError
from odoo.osv import expression


class WebsiteNewsletterForm(WebsiteForm):

    def _handle_website_form(self, model_name, **kwargs):
        """We override this method to update an existing mailing contact if it exists"""
        if model_name == 'mailing.contact':
            model_record = request.env.ref('mass_mailing.model_mailing_contact')
            searchable_fields = request.env[model_name]._get_searchable_fields()

            domain = expression.OR([
                [(field, '=', value)]
                for field, value in kwargs.items()
                if field in searchable_fields])

            if not domain:
                raise ValidationError(_('Domain cannot be empty'))

            contact = request.env['mailing.contact'].sudo().search(domain)
            if contact:
                try:
                    data = self.extract_data(model_record, kwargs)
                except ValidationError as e:
                    return json.dumps({'error_fields': e.args[0]})

                contact.write(data['record'])
                return json.dumps({'id': contact.id})

        return super()._handle_website_form(model_name, **kwargs)
