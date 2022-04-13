# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    subcontracting_location = fields.Boolean(
        'Is a Subcontracting Location?', default=False,
        help='Check this box to create a new dedicated subcontracting location for this company. Note that standard subcontracting routes will be adapted so as to take these into account automatically.'
    )

    @api.constrains('subcontracting_location', 'usage', 'location_id')
    def _check_subcontracting_location(self):
        for location in self:
            if location.subcontracting_location and (location.usage != 'internal' or location.warehouse_id):
                raise ValidationError(_("Note that a subcontracting location should ideally be of type Internal, and be linked to the appropriate company, but not to any specific warehouse, so that stock can be managed accurately."))

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        new_subcontracting_locations = res.filtered(lambda location: location.subcontracting_location)
        new_subcontracting_locations._activate_subcontracting_location_rules()
        return res

    def write(self, values):
        if 'subcontracting_location' in values:
            if self.filtered(lambda location: location == location.company_id.subcontracting_location_id):
                raise ValidationError(_("You cannot alter the company's subcontracting location"))
            if not values['subcontracting_location'] and self.env['res.partner'].search([('property_stock_subcontractor', 'in', self.ids)]):
                raise ValidationError(_("You cannot change the subcontracting location as it is still linked to a subcontractor partner"))

        res = super().write(values)
        if 'subcontracting_location' in values:
            if values['subcontracting_location']:
                self._activate_subcontracting_location_rules()
            else:
                self._archive_subcontracting_location_rules()
        return res

    def _check_access_putaway(self):
        """ Use sudo mode for subcontractor """
        if self.env.user.partner_id.is_subcontractor:
            return self.sudo()
        else:
            return super()._check_access_putaway()

    def _archive_subcontracting_location_rules(self):
        reference_location_ids = self.company_id.subcontracting_location_id
        reference_rules = self.env['stock.rule'].search(['|', ('location_src_id', 'in', reference_location_ids.ids), ('location_dest_id', 'in', reference_location_ids.ids)])
        reference_routes = reference_rules.route_id
        rules_to_archive = self.env['stock.rule'].search(['&', ('route_id', 'in', reference_routes.ids), '|', ('location_src_id', 'in', self.ids), ('location_dest_id', 'in', self.ids)])
        rules_to_archive.action_archive()

    def _activate_subcontracting_location_rules(self):
        """ Create or unarchive rules for the subcontracting location(s)."""
        locations_per_company = {}
        for location in self:
            if location != location.company_id.subcontracting_location_id:
                locations_per_company.setdefault(location.company_id, []).extend(location)
        new_rules_vals = []
        rules_to_unarchive = self.env['stock.rule']
        for company, locations in locations_per_company.items():
            reference_location_id = company.subcontracting_location_id
            if reference_location_id:
                reference_rules_from = self.env['stock.rule'].search([('location_src_id', '=', reference_location_id.id)])
                reference_rules_to = self.env['stock.rule'].search([('location_dest_id', '=', reference_location_id.id)])
                for location in locations:
                    existing_rules = {
                        (rule.route_id, rule.picking_type_id, rule.action, rule.location_src_id): rule
                        for rule in self.env['stock.rule'].with_context(active_test=False).search([('location_src_id', '=', location.id)])
                    }
                    for rule in reference_rules_from:
                        if (rule.route_id, rule.picking_type_id, rule.action, location) not in existing_rules:
                            new_rules_vals.append(rule.copy_data({
                                'location_src_id': location.id,
                                'name': rule.name.replace(reference_location_id.name, location.name)
                            })[0])
                        else:
                            existing_rule = existing_rules[(rule.route_id, rule.picking_type_id, rule.action, location)]
                            if not existing_rule.active:
                                rules_to_unarchive += existing_rule
                    existing_rules = {
                        (rule.route_id, rule.picking_type_id, rule.action, rule.location_dest_id): rule
                        for rule in self.env['stock.rule'].with_context(active_test=False).search([('location_dest_id', '=', location.id)])
                    }
                    for rule in reference_rules_to:
                        if (rule.route_id, rule.picking_type_id, rule.action, location) not in existing_rules:
                            new_rules_vals.append(rule.copy_data({
                                'location_dest_id': location.id,
                                'name': rule.name.replace(reference_location_id.name, location.name)
                            })[0])
                        else:
                            existing_rule = existing_rules[(rule.route_id, rule.picking_type_id, rule.action, location)]
                            if not existing_rule.active:
                                rules_to_unarchive += existing_rule
        self.env['stock.rule'].create(new_rules_vals)
        rules_to_unarchive.action_unarchive()
