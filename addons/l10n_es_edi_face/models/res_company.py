# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    l10n_es_edi_face_person_type = fields.Char(
            string='FACe EDI Person Type Code',
            size=1,
            compute='_compute_l10n_es_edi_face_person_type',
            store=False,
    )
    l10n_es_edi_face_residence_type = fields.Char(
            string='FACe EDI Residency Type Code',
            compute='_compute_l10n_es_edi_face_residence_type',
            store=False,
    )

    l10n_es_edi_face_cif_nif_nie = fields.Char(string='FACe EDI Non-VAT Tax Identifier (CIF/NIF/NIE)')

    l10n_es_edi_face_tax_identifier = fields.Char(
            string='FACe EDI Tax Identifier',
            compute='_compute_l10n_es_edi_face_tax_identifier',
            store=False
    )

    def _compute_l10n_es_edi_face_person_type(self):
        for partner in self:
            partner.l10n_es_edi_face_person_type = 'J'

    @api.depends('country_id')
    def _compute_l10n_es_edi_face_residence_type(self):
        eu_countries_ids = self.env['res.country.group'].search([('name', '=', 'Europe')]).country_ids.ids
        for partner in self:
            country = partner.country_id
            partner.l10n_es_edi_face_residence_type = \
                'R' if country.code == 'ES' else 'U' if country.id in eu_countries_ids else "E"

    @api.depends('vat', 'l10n_es_edi_face_cif_nif_nie')
    def _compute_l10n_es_edi_face_tax_identifier(self):
        for partner in self:
            partner.l10n_es_edi_face_tax_identifier = partner.vat or partner.l10n_es_edi_face_cif_nif_nie
