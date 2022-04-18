from odoo import api, fields, models


# It is not possible to use res.city because there is no city in Turkish standard address
# see.: https://postakodu.ptt.gov.tr/Dosyalar/adres.pdf

class TrResArea(models.Model):
    _name = "l10n_tr.area"
    _description = "Area"

    name = fields.Char()
    city_id = fields.Many2one(comodel_name='res.city')
    zipcode = fields.Char(size=5)

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = list(args or [])
        if not (name == '' and operator == 'ilike'):
            args += ['|', (self._rec_name, operator, name), ('zipcode', operator, name)]
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)


class TrResNeighborhood(models.Model):
    _name = "l10n_tr.neighborhood"
    _description = "Neighborhood"

    name = fields.Char()
    area_id = fields.Many2one(comodel_name='l10n_tr.area')
    zipcode = fields.Char(related='area_id.zipcode')
    display_name = fields.Char(related='name')

    def name_get(self):
        res = []
        for nbh in self:
            name = nbh.name if not nbh.zipcode else '%s (%s)' % (nbh.name, nbh.zipcode)
            res.append((nbh.id, name))
        return res

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = list(args or [])
        if not (name == '' and operator == 'ilike'):
            args += ['|', (self._rec_name, operator, name), ('zipcode', operator, name)]
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
