# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import route, request
from odoo.addons.mass_mailing.controllers import main


class MassMailController(main.MassMailController):

    @route('/website_mass_mailing/is_subscriber', type='json', website=True, auth="public")
    def is_subscriber(self, list_id, input_name, **post):
        value = self.set_default_input_value(input_name)

        is_subscriber = False
        if value:
            contacts_count = request.env['mailing.contact.subscription'].sudo().search_count([('list_id', 'in', [int(list_id)]), ('contact_id.' + input_name, '=', value), ('opt_out', '=', False)])
            is_subscriber = contacts_count > 0

        return {'is_subscriber': is_subscriber, 'value': value}

    def set_default_input_value(self, input_name):
        value = None
        if input_name == 'email':
            if not request.env.user._is_public():
                value = request.env.user.email
            elif request.session.get('mass_mailing_email'):
                value = request.session['mass_mailing_email']
        return value

    @route('/website_mass_mailing/subscribe', type='json', website=True, auth="public")
    def subscribe(self, list_id, value, input_name, **post):
        if not request.env['ir.http']._verify_request_recaptcha_token('website_mass_mailing_subscribe'):
            return {
                'toast_type': 'danger',
                'toast_content': _("Suspicious activity detected by Google reCaptcha."),
            }
        ContactSubscription = request.env['mailing.contact.subscription'].sudo()
        Contacts = request.env['mailing.contact'].sudo()
        name, value = Contacts.get_name_email(value) if input_name == 'email' else value, value

        subscription = ContactSubscription.search([('list_id', '=', int(list_id)), ('contact_id.' + input_name, '=', value)], limit=1)
        if not subscription:
            # inline add_to_list as we've already called half of it
            contact_id = Contacts.search([(input_name, '=', value)], limit=1)
            if not contact_id:
                contact_id = Contacts.create({'name': name, input_name: value})
            ContactSubscription.create({'contact_id': contact_id.id, 'list_id': int(list_id)})
        elif subscription.opt_out:
            subscription.opt_out = False
        # add email to session
        request.session['mass_mailing_' + input_name] = value
        return {
            'toast_type': 'success',
            'toast_content': _("Thanks for subscribing!"),
        }
