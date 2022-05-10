# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Microsoft Outlook",
    "version": "1.1",
    "category": "Hidden",
    "description": "Outlook support for outgoing mail servers",
    "depends": [
        "mail",
    ],
    "data": [
        "views/ir_mail_server_views.xml",
        "views/res_config_settings_views.xml",
        "views/templates.xml",
    ],
    "auto_install": False,
    "license": "LGPL-3",
}
