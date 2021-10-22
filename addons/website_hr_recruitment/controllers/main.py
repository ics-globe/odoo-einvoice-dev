# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.osv.expression import AND
from odoo.http import request
from werkzeug.exceptions import NotFound


class WebsiteHrRecruitment(http.Controller):
    _jobs_per_page = 12

    def sitemap_jobs(env, rule, qs):
        if not qs or qs.lower() in '/jobs':
            yield {'loc': '/jobs'}

    @http.route([
        '/jobs',
        '/jobs/page/<int:page>',
        '/jobs/country/<model("res.country"):country>',
        '/jobs/country/<model("res.country"):country>/page/<int:page>',
        '/jobs/department/<model("hr.department"):department>',
        '/jobs/department/<model("hr.department"):department>/page/<int:page>',
        '/jobs/country/<model("res.country"):country>/department/<model("hr.department"):department>',
        '/jobs/country/<model("res.country"):country>/department/<model("hr.department"):department>/page/<int:page>',
        '/jobs/office/<int:office_id>',
        '/jobs/office/<int:office_id>/page/<int:page>',
        '/jobs/country/<model("res.country"):country>/office/<int:office_id>',
        '/jobs/country/<model("res.country"):country>/office/<int:office_id>/page/<int:page>',
        '/jobs/department/<model("hr.department"):department>/office/<int:office_id>',
        '/jobs/department/<model("hr.department"):department>/office/<int:office_id>/page/<int:page>',
        '/jobs/country/<model("res.country"):country>/department/<model("hr.department"):department>/office/<int:office_id>',
        '/jobs/country/<model("res.country"):country>/department/<model("hr.department"):department>/office/<int:office_id>/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=sitemap_jobs)
    def jobs(self, country=None, department=None, office_id=None, page=1, search=None, **kwargs):
        env = request.env(context=dict(request.env.context, show_address=True, no_tag_br=True))

        Country = env['res.country']
        Jobs = env['hr.job']

        # Default search by user country
        if not (country or department or office_id or kwargs.get('all_countries')):
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                countries_ = Country.search([('code', '=', country_code)])
                country = countries_[0] if countries_ else None
                if country:
                    country_count = Jobs.search_count(AND([
                        request.website.website_domain(),
                        [('address_id.country_id', '=', country.id)]
                    ]))
                    if not country_count:
                        country = False

        options = {
            'displayDescription': True,
            'allowFuzzy': not request.params.get('noFuzzy'),
            'country': str(country.id) if country else None,
            'department': str(department.id) if department else None,
            'office_id': office_id,
        }
        total, details, fuzzy_search_term = request.website._search_with_fuzzy("jobs", search,
            limit=page * self._jobs_per_page, order="is_published desc, sequence, no_of_recruitment desc", options=options)
        # Browse jobs as superuser, because address is restricted
        jobs = details[0].get('results', Jobs).sudo()

        # Deduce offices, departments and countries offices of those jobs
        offices = set(j.address_id for j in jobs if j.address_id)
        departments = set(j.department_id for j in jobs if j.department_id)
        countries = set(o.country_id for o in offices if o.country_id)

        total = len(jobs)
        pager = request.website.pager(
            url=request.httprequest.path.partition('/page/')[0],
            url_args={'search': search},
            total=total,
            page=page,
            step=self._jobs_per_page,
        )
        offset = pager['offset']
        jobs = jobs[offset:offset + self._jobs_per_page]

        # Render page
        return request.render("website_hr_recruitment.index", {
            'jobs': jobs,
            'countries': countries,
            'departments': departments,
            'offices': offices,
            'country_id': country,
            'current_country_id': country.name if country else 0,
            'current_country': country or False,
            'department_id': department,
            'current_department_id': department.name if department else 0,
            'current_department': department or False,
            'office_id': office_id,
            'current_office_id': office_id if office_id else 0,
            'current_office': office_id or False,
            'pager': pager,
            'search': fuzzy_search_term or search,
            'search_count': total,
            'original_search': fuzzy_search_term and search,
        })

    @http.route('/jobs/add', type='http', auth="user", website=True)
    def jobs_add(self, **kwargs):
        # avoid branding of website_description by setting rendering_bundle in context
        job = request.env['hr.job'].with_context(rendering_bundle=True).create({
            'name': _('Job Title'),
        })
        return request.redirect("/jobs/detail/%s?enable_editor=1" % slug(job))

    @http.route('''/jobs/detail/<model("hr.job"):job>''', type='http', auth="public", website=True, sitemap=True)
    def jobs_detail(self, job, **kwargs):
        return request.render("website_hr_recruitment.detail", {
            'job': job,
            'main_object': job,
        })

    @http.route('''/jobs/apply/<model("hr.job"):job>''', type='http', auth="public", website=True, sitemap=True)
    def jobs_apply(self, job, **kwargs):
        error = {}
        default = {}
        if 'website_hr_recruitment_error' in request.session:
            error = request.session.pop('website_hr_recruitment_error')
            default = request.session.pop('website_hr_recruitment_default')
        return request.render("website_hr_recruitment.apply", {
            'job': job,
            'error': error,
            'default': default,
        })
