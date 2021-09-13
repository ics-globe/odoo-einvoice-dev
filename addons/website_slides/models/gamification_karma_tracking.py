# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class KarmaTracking(models.Model):
    _inherit = 'gamification.karma.tracking'

    def _get_selection_origin(self):
        return (
            super(KarmaTracking, self)._get_selection_origin()
            + [('slide.slide', 'Quiz'), ('slide.channel', self.env['slide.channel']._description)]
        )
