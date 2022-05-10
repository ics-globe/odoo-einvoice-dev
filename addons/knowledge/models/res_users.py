# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class Users(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        users = super(Users, self).create(vals_list)
        users.filtered(lambda user: not user.share)._generate_tutorial_articles()
        return users

    def _generate_tutorial_articles(self):
        article_template = self.sudo().env.ref('knowledge.knowledge_article_welcome', raise_if_not_found=False)
        if not article_template:
            return
        articles_to_create = [{
            'name': '%s %s' % (article_template.name, user.name),
            'body': article_template.body,
            'icon': article_template.icon,
            'internal_permission': 'none',
            'article_member_ids': [(0, 0, {
                'partner_id': user.partner_id.id,
                'permission': 'write'
            })]
        } for user in self]
        if articles_to_create:
            self.env['knowledge.article'].sudo().create(articles_to_create)
