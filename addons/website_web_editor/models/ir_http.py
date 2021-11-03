# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _load_web_editor_qs(cls):
        keys = super()._load_web_editor_qs()
        if request.is_frontend_multilang and request.lang == cls._get_default_lang():
            keys['edit_translations'] = False
        return keys

    @classmethod
    def _frontend_pre_dispatch(cls):
        super()._frontend_pre_dispatch()
        keys = cls._load_web_editor_qs()
        request.update_context(**keys)
