# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.osv import expression

from odoo.addons.website_profile.controllers.main import WebsiteProfile

class WebsiteSlidesSurvey(WebsiteProfile):
    def _check_user_certification_attempts_access(self, values):
        if 'user' not in values:
            return False
        return values['user'].id == request.env.user.id or \
            request.env.user.has_group('survey.group_survey_manager')

    def _prepare_user_profile_values(self, user, **kwargs):
        """Loads all data required to display the certification attempts of the given user"""
        values = super(WebsiteSlidesSurvey, self)._prepare_user_profile_values(user, **kwargs)
        values['show_certification_tab'] = self._check_user_certification_attempts_access(values)
        if not values['show_certification_tab']:
            return values

        domain = ['&',
            ('survey_id.certification', '=', True),
            '|',
                ('email', 'in', values['user'].mapped('email')),
                ('partner_id', 'in', values['user'].mapped('partner_id').mapped('id'))
        ]

        if 'search' in kwargs:
            values['certification_search_terms'] = kwargs['search']
            domain = expression.AND([domain,
                [('survey_id.title', 'ilike', kwargs['search'])]
            ])

        certifications_attempts = []
        attempt_number = 1
        current_survey_id = False
        user_input_sudo = request.env['survey.user_input'].sudo()

        for user_input in user_input_sudo.search(domain, order='survey_id asc, create_date asc'):
            survey_id = user_input.survey_id.id
            if not current_survey_id or current_survey_id != survey_id:
                attempt_number = 1
                current_survey_id = survey_id
            certifications_attempts.append({
                'user_input': user_input,
                'attempt_number': attempt_number
            })
            attempt_number += 1

        order_by = kwargs.get('order', 'create_date')
        if order_by == 'create_date':
            certifications_attempts.sort(key=lambda e: e['user_input'].create_date, reverse=True) # inplace

        values['certification_attempts'] = certifications_attempts
        return values
