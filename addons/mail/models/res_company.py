# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, tools


class Company(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    def _get_default_alias_domain_id(self):
        return self.env['mail.alias.domain'].search([], limit=1).id

    # alias_domain_ids = fields.One2many('mail.alias.domain', 'company_id', 'Alias Domains')
    # alias_domain_id = fields.Many2one(
    #     'mail.alias.domain', 'Alias Domain',
    #     compute='_compute_alias_domain_id', readonly=False, store=True)
    alias_domain_id = fields.Many2one(
        'mail.alias.domain', string='Alias Domain', ondelete='set null',
        default=lambda self: self._get_default_alias_domain_id())
    alias_domain_name = fields.Char('Alias Domain Name', related='alias_domain_id.name', readonly=True, store=True)
    bounce_email = fields.Char(string="Bounce Email", compute="_compute_bounce")
    bounce_formatted = fields.Char(string="Bounce", compute="_compute_bounce")
    catchall_email = fields.Char(string="Catchall Email", compute="_compute_catchall")
    catchall_formatted = fields.Char(string="Catchall", compute="_compute_catchall")
    email_formatted = fields.Char(string="Formatted Email", compute="_compute_email_formatted")

    # @api.depends('alias_domain_ids.company_id')
    # def _compute_alias_domain_id(self):
    #     companies_generic = self.filtered(lambda company: not company.alias_domain_ids)
    #     if companies_generic:
    #         generic_domain = self.env['mail.alias.domain'].search([('company_id', '=', False)], limit=1, order='id desc')
    #         companies_generic.alias_domain_id = generic_domain
    #     for company in self - companies_generic:
    #         company.alias_domain_id = company.alias_domain_ids[0]

    # @api.depends('alias_domain_id.name')
    # def _compute_alias_domain_name(self):
    #     for company in self:
    #         if company.alias_domain_id:
    #             company.alias_domain_name = company.alias_domain_id.name
    #         else:
    #             company.alias_domain_name = False

    @api.depends('alias_domain_id.bounce', 'alias_domain_id.name')
    def _compute_bounce(self):
        self.bounce_email = ''
        self.bounce_formatted = ''

        for company in self:
            if company.alias_domain_id:
                bounce_email = '%s@%s' % (company.alias_domain_id.bounce, company.alias_domain_id.name)
                company.bounce_email = bounce_email
                company.bounce_formatted = tools.formataddr((company.name, company.bounce_email))

    @api.depends('alias_domain_id.catchall', 'alias_domain_id.name')
    def _compute_catchall(self):
        self.catchall_email = ''
        self.catchall_formatted = ''

        for company in self:
            if company.alias_domain_id:
                catchall_email = '%s@%s' % (company.alias_domain_id.catchall, company.alias_domain_id.name)
                company.catchall_email = catchall_email
                company.catchall_formatted = tools.formataddr((company.name, company.catchall_email))

    @api.depends('partner_id.email_formatted', 'catchall_formatted')
    def _compute_email_formatted(self):
        for company in self:
            if company.partner_id.email_formatted:
                company.email_formatted = company.partner_id.email_formatted
            elif company.catchall_formatted:
                company.email_formatted = company.catchall_formatted
            else:
                company.email_formatted = ''
