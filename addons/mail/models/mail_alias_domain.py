# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _


class AliasDomain(models.Model):
    """ Model alias domain (old ``mail.alias.domain`` configuration parameter)
    to be company-specific. """
    _name = 'mail.alias.domain'
    _description = "Email Domain"
    _order = 'id ASC'
    _rec_name = 'name'

    name = fields.Char('Name', required=True)
    # company_id = fields.Many2one('res.company', string='Company')
    company_ids = fields.One2many('res.company', 'alias_domain_id', string='Used in')

    # @api.constrains('company_id')
    # def _constrains_company(self):
    #     """ Do not allow more than one company specific alias domain. Perform
    #     a global search as anyway we won't have much alias domains stored. """
    #     company_specific = self.search([('company_id', '!=', False)])
    #     company_to_domains = {}
    #     for domain in company_specific:
    #         company_to_domains.setdefault(domain.company_id, self.env['mail.alias.domain'])
    #         company_to_domains[domain.company_id] += domain

    #     duplicates = [company for company, domains in company_to_domains.items() if len(domains) > 1]
    #     if duplicates:
    #         raise exceptions.ValidationError(
    #             _("You are trying to create duplicate alias domain(s). We found that alias domains for %(company_names)s already exist.",
    #               company_names=", ".join(company.name for company in duplicates)
    #              ))

    # @api.model_create_multi
    # def create(self, vals_list):
    #     domains = super(AliasDomain, self).create(vals_list)
    #     if any(not domain.company_id for domain in domains):
    #         self.env['res.company'].search([('alias_domain_id', '=', False)])._compute_alias_domain_id()
    #     return domains

    @api.model_create_multi
    def create(self, vals_list):
        domains = super(AliasDomain, self).create(vals_list)
        if domains:
            self.env['res.company'].search([('alias_domain_id', '=', False)]).alias_domain_id = domains[0]
        return domains
