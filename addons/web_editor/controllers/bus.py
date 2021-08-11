# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import SUPERUSER_ID, tools
from odoo.http import request, route
from odoo.addons.bus.controllers.main import BusController


class EditorCollaborationController(BusController):
    # ---------------------------
    # Extends BUS Controller Poll
    # ---------------------------
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            # Do not alter original list.
            channels = list(channels)
            for channel in channels:
                if isinstance(channel, str):
                    match = re.match('editor_collaboration:(\w+(?:.\w+)*):(\w+):([\d]+)', channel)
                    if (match):
                        model_name = match[1]
                        field_name = match[2]
                        res_id = int(match[3])

                        document = request.env[model_name].browse([res_id])

                        document.check_access_rights('read')
                        document.check_field_access_rights('read', [field_name])
                        document.check_access_rule('read')
                        document.check_access_rights('write')
                        document.check_field_access_rights('write', [field_name])
                        document.check_access_rule('write')

                        channels.append((request.db, 'editor_collaboration', model_name, field_name, res_id))
        return super(EditorCollaborationController, self)._poll(dbname, channels, last, options)