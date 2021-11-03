# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _load_web_editor_qs(cls):
        keys = {}
        for key in ['editable', 'edit_translations', 'translatable']:
            if key in request.httprequest.args and key not in request.env.context:
                keys[key] = True
        return keys

    @classmethod
    def _pre_dispatch(cls, rule, args):
        super()._frontend_pre_dispatch()
        keys = cls._load_web_editor_qs()
        request.update_context(**keys)

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super(IrHttp, cls)._get_translation_frontend_modules_name()
        return mods + ['web_editor']
