from odoo import api, fields, models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _accumulate_amounts(self, data):
        res = super(PosSession, self)._accumulate_amounts(data)
        print('ok')
        return res
