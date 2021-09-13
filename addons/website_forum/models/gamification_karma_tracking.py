# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class KarmaTracking(models.Model):
    _inherit = 'gamification.karma.tracking'

    def _get_selection_origin(self):
        return super()._get_selection_origin() + [('forum.post', self.env['forum.post']._description)]
