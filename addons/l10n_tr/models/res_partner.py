from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_tr_tax_office_id = fields.Many2one(comodel_name='l10n_tr.tax_office', string='Tax Office')
    l10n_tr_area_id = fields.Many2one(comodel_name='l10n_tr.area', compute="_compute_l10n_tr_area_id",
                                      inverse="_inverse_l10n_area_id", readonly=False, store=True)
    city_id = fields.Many2one(comodel_name='res.city', readonly=False)
    l10n_tr_neighborhood_id = fields.Many2one(comodel_name='l10n_tr.neighborhood')
    l10n_tr_postal_box = fields.Char(string="P.O. box")

    @api.model
    def _address_fields(self):
        return super()._address_fields() + ['l10n_tr_area_id', 'city_id', 'l10n_tr_neighborhood_id',
                                            'l10n_tr_tax_office_id']

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_tr_tax_office_id']

    def _display_address_depends(self):
        return super()._display_address_depends() + [
            'l10n_tr_tax_office_id',
            'city_id', 'l10n_tr_area_id', 'l10n_tr_neighborhood_id'
        ]

    def _prepare_display_address(self, without_company=False):
        address_format, args = super()._prepare_display_address(without_company=without_company)

        args.update({
            'l10n_tr_area_name': self.l10n_tr_area_id.name or '',
            'l10n_tr_neighborhood_name': self.l10n_tr_neighborhood_id.name or '',
            'l10n_tr_tax_office_name': self.l10n_tr_tax_office_id.name or '',
        })
        return address_format, args

    @api.onchange('state_id')
    def _onchange_state(self):
        # override
        res = super()._onchange_state()
        if self.country_id == self.env.ref('base.tr'):
            if self.city_id.state_id != self.state_id:
                self.city_id = False
                self.city = ''
                self.street2 = ''
                self.zip = ''
                self.l10n_tr_area_id = False
                self.l10n_tr_neighborhood_id = False
        return res

    # logic: if state, district or area are not set, setting neighborhood will set them respectfully
    # if any of them is filled, the domains are limited by them

    @api.onchange('city_id')
    def _onchange_city_id(self):
        # override
        res = super()._onchange_city_id()
        if self.country_id == self.env.ref('base.tr'):
            if self.l10n_tr_area_id.city_id != self.city_id:
                self.l10n_tr_area_id = False
                self.l10n_tr_neighborhood_id = False
                self.street2 = ''
            area = self.l10n_tr_area_id.name or ''
            district = self.city_id.name or ''
            self.city = district if area == district else f"{area} {district}"
            self.zip = self.l10n_tr_area_id.zipcode or False
        return res

    @api.depends('l10n_tr_neighborhood_id')
    def _compute_l10n_tr_area_id(self):
        for rec in self:
            if rec.l10n_tr_neighborhood_id:
                rec.l10n_tr_area_id = rec.l10n_tr_neighborhood_id.area_id
                rec.street2 = rec.l10n_tr_neighborhood_id.name

    @api.onchange('l10n_tr_area_id')
    def _inverse_l10n_area_id(self):
        for rec in self:
            if rec.l10n_tr_area_id and rec.city_id != rec.l10n_tr_area_id.city_id:
                rec.city_id = rec.l10n_tr_area_id.city_id
                rec.zip = rec.l10n_tr_area_id.zipcode
            if rec.l10n_tr_neighborhood_id and rec.l10n_tr_neighborhood_id.area_id != rec.l10n_tr_area_id:
                rec.l10n_tr_neighborhood_id = False
                rec.street2 = ''

    def _get_name(self):
        name = super()._get_name()
        if self._context.get('show_vat') and self.vat and self.l10n_tr_tax_office_id:
            name = "%s - %s" % (name, self.l10n_tr_tax_office_id.name)
        return name
