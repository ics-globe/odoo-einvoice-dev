# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.tools import mute_logger


@odoo.tests.common.tagged('post_install', '-at_install')
class TestMedia(odoo.tests.HttpCase):

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_01_image_link(self):
        self.start_tour("/", 'test_image_link', login="admin")
