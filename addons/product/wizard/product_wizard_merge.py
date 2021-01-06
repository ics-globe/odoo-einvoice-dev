# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
import functools
import itertools
import logging
import psycopg2
import datetime

from odoo import api, fields, models, Command
from odoo import _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class ProductWizardMerge(models.TransientModel):
    """
        The function of this wizard is to configure the product merge. It allows
        the merge of product template by merging certain product.products or by
        keeping them with addition of new characteristics.
    """

    _name = 'product.wizard.merge'
    _description = 'Merge Product Wizard'

    dst_product_tmpl_id = fields.Many2one('product.template', string='Destination', required=True, domain="[('id', 'in', src_product_tmpl_ids)]", ondelete='cascade')
    src_product_tmpl_ids = fields.Many2many('product.template', relation='product_wizard_merge_src_templates_rel', string='Sources', readonly=True)
    pwml_ids = fields.One2many('product.wizard.merge.line', 'wizard_id', string='Lines')
    pwma_ids = fields.One2many('product.wizard.merge.attribute', 'wizard_id', string='Attributes after merge')
    pwmav_ids = fields.Many2many('product.wizard.merge.attribute.value', compute="_compute_pwmav_ids", string='Values')

    nb_variants = fields.Integer(compute='_compute_nb_variants', string='Number of variants before merge')
    possible_nb_variants = fields.Integer(compute='_compute_pwmav_ids', string='Number of variants possible by this combination')
    after_merge_nb_variants = fields.Integer(compute='_compute_nb_of_variants', string='Number of variants after merge')

    will_merge_products = fields.Boolean(compute="_compute_state", string='Will merge with')
    has_error = fields.Boolean(compute="_compute_state", string='Values missing')

    add_attribute_id = fields.Many2one('product.attribute', string='Add an attribute', store=False)
    add_value_id = fields.Many2one('product.attribute.value', string='Select the value', store=False)

    add_pwmav_id = fields.Many2one('product.wizard.merge.attribute.value', string='Add value on selected variants', store=False)
    available_selected_pwmav_ids = fields.Many2many('product.wizard.merge.attribute.value', compute="_onchange_selected", string='Available values for selected variants')

    @api.depends("pwma_ids", "pwma_ids.pwmav_ids")
    def _compute_pwmav_ids(self):
        """ Compute the list off all defined values and the possible variants.
        """
        for wizard in self:
            pwmavs = self.env['product.wizard.merge.attribute.value']
            nb = 1
            for pwma in wizard.pwma_ids:
                pwmavs += pwma.pwmav_ids
                nb *= len(pwma.pwmav_ids) or 1
            wizard.pwmav_ids = pwmavs
            wizard.possible_nb_variants = nb

    @api.onchange("pwml_ids")
    def _compute_nb_variants(self):
        """ Compute the number of variants
        """
        self.nb_variants = len(self.pwml_ids)

    @api.depends("pwml_ids", "pwml_ids.will_merge_pwml_ids")
    def _compute_nb_of_variants(self):
        """ Compute the the number of variant after merge.
        """
        for wizard in self:
            pwmls = wizard.pwml_ids
            for pwml in wizard.pwml_ids:
                if pwml in pwmls and pwml.will_merge_pwml_ids:
                    pwmls -= pwml.will_merge_pwml_ids
            wizard.after_merge_nb_variants = len(pwmls)

    @api.depends("pwml_ids", "pwml_ids.available_pwmav_ids")
    def _compute_state(self):
        """ Compute error message and found the product will be merged.
        """
        for wizard in self:
            will_merge_products = False
            has_error = False
            pwml = self.env['product.wizard.merge.line']

            for pwml_self in wizard.pwml_ids:
                if pwml_self.has_error:
                    has_error = True

                pwml += pwml_self
                will_merge_pwml_ids = self.env['product.wizard.merge.line']
                for pwml_other in wizard.pwml_ids:
                    if pwml_self != pwml_other and set(pwml_other.pwmav_ids.ids) == set(pwml_self.pwmav_ids.ids):
                        will_merge_pwml_ids += pwml_other

                pwml_self.will_merge_pwml_ids = will_merge_pwml_ids
                if will_merge_pwml_ids:
                    will_merge_products = True

            wizard.pwml_ids = pwml
            wizard.will_merge_products = will_merge_products
            wizard.has_error = has_error

    @api.onchange("pwma_ids")
    def _onchange_pwmav_ids(self):
        """ When the user change the value, the field trigger_update_pwmav is updated.
            The line where this field is true, is the destination of the
            attribute value. This method remove the attribute value from the
            previous attributes. And if theyr are already an attribute value
            with the same 'product.attribute.value', they remove the new one
            and udpdate all product line in the wizard.
        """
        # Check if it's attribute value change
        moved = False
        for attribute in self.pwma_ids:
            if attribute.pwmav_ids != attribute.previous_pwmav_ids:
                moved = True
        if not moved:
            return

        for attribute in self.pwma_ids:
            # Remove value from the original attribute position.
            if attribute.pwmav_ids != attribute.previous_pwmav_ids:
                moved_pwmav = attribute.pwmav_ids - attribute.previous_pwmav_ids

                # Remove the moved value from the other attributes.
                for other in self.pwma_ids:
                    if other != attribute:
                        other.pwmav_ids -= moved_pwmav

                # Find duplicates to remove it.
                for pwmav in moved_pwmav:
                    value_to_keep = attribute.pwmav_ids.filtered(lambda v: v.value_id == pwmav.value_id) - pwmav

                    if value_to_keep:
                        # Remove useless newest value.
                        attribute.pwmav_ids -= pwmav

                        # Add for merge of attribute values.
                        value_to_keep.merged_ptav_ids += pwmav.ptav_id

                        # Update the product values.
                        for pwml in self.pwml_ids:
                            if pwml.pwmav_ids & pwmav:
                                pwml.pwmav_ids = pwml.pwmav_ids - pwmav + value_to_keep

                    pwmav.pwma_id = attribute.id

                # Reset previous value field.
                attribute.previous_pwmav_ids = attribute.pwmav_ids

        # Remove empty attributes.
        for attribute in self.pwma_ids:
            if not attribute.pwmav_ids:
                self.pwma_ids -= attribute

        # Unset the removed values.
        all_pwmav = self.pwma_ids.pwmav_ids
        for pwml in self.pwml_ids:
            to_unset = pwml.pwmav_ids - all_pwmav
            if to_unset:
                pwml.pwmav_ids -= to_unset

        self._compute_state()

    @api.onchange("add_pwmav_id")
    def _onchange_add_pwmav_id(self):
        """ Add the 'add value' to all product who match with the selected
            product template. Then reset the 3 add fields.
        """
        for line in self.pwml_ids:
            if line.selected:
                line.pwmav_ids += self.add_pwmav_id
                line.selected = False
        self.add_pwmav_id = False

    @api.onchange("add_value_id")
    def _onchange_add_value_id(self):
        """ Create the new attribute and his value. This reacord are created in
            database because it's refer in other model in the same wizard view.
            It's important to know that this onchange clear the cache.
            Then reset the 3 add fields.
        """
        if self.add_attribute_id and self.add_value_id:
            PWMA = self.env['product.wizard.merge.attribute']
            pwma = PWMA.create({
                'wizard_id': self._origin.id,
                'attribute_id': self.add_attribute_id.id,
            })
            PWMA = self.env['product.wizard.merge.attribute.value']
            PWMA.create({
                'wizard_id': self._origin.id,
                'pwma_id': pwma.id,
                'value_id': self.add_value_id.id,
            })
            self.pwma_ids += pwma
        self.add_attribute_id = False
        self.add_value_id = False

    @api.onchange("pwml_ids")
    def _onchange_selected(self):
        """ Compute the available value to add.
        """
        pwmavs = self.env['product.wizard.merge.attribute.value']
        for pwml in self.pwml_ids:
            if pwml.selected:
                pwmavs += pwml.available_pwmav_ids
        self.available_selected_pwmav_ids = pwmavs

    @api.model
    def _action_open_wizard_merge(self, records):
        """ Prepare and create the wizard to configure the future product merge.
        """
        self = self.with_context(active_test=False)
        dst_template = self.env['product.template']
        src_templates = self.env['product.template']
        if records._name == 'product.product':
            src_templates = records.mapped('product_tmpl_id')
        else:
            src_templates = records

        src_templates = src_templates.sorted(lambda pt: pt.id)
        dst_template = src_templates[0]

        wizard = self.create({
            'dst_product_tmpl_id': dst_template.id,
            'src_product_tmpl_ids': (src_templates + dst_template).ids,
        })

        PTAV = self.env['product.template.attribute.value']
        # PAV = self.env['product.attribute.value']
        PWMA = self.env['product.wizard.merge.attribute']
        PWMAV = self.env['product.wizard.merge.attribute.value']
        PWML = self.env['product.wizard.merge.line']

        for p in src_templates.mapped('product_variant_ids'):
            line = PWML.create({
                'wizard_id': wizard.id,
                'product_id': p.id,
            })

            for value in PTAV.search([('ptav_product_variant_ids', 'in', p.ids)]):
                pwmav = PWMAV
                pwma_id = PWMA.search([('wizard_id', '=', wizard.id), ('ptal_id', '=', value.attribute_line_id.id)])

                if not pwma_id:
                    pwma_id = PWMA.create({
                        'wizard_id': wizard.id,
                        'attribute_id': value.attribute_line_id.attribute_id.id,
                        'ptal_id': value.attribute_line_id.id,
                    })
                else:
                    pwmav = PWMAV.search([('pwma_id', '=', pwma_id.id), ('ptav_id', '=', value.id)])

                if not pwmav:
                    pwmav = PWMAV.create({
                        'wizard_id': wizard.id,
                        'pwma_id': pwma_id.id,
                        'value_id': value.product_attribute_value_id.id,
                        'ptav_id': value.id,
                    })

                pwma_id.pwmav_ids += pwmav
                line.pwmav_ids += pwmav

        return {
            'name': _("Merge product template"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'product.wizard.merge',
            'res_id': wizard.id,
            'context': {
                'default_wizard_id': wizard.id,
                'active_test': False,
                'merge_product_template': True,
                'update_product_template_attribute_values': False,
            }
        }

    def action_merge(self):
        """ Apply the merge with the selected configuration.
        """
        if self.has_error:
            raise ValidationError(_('Please check all values before merge.'))

        _logger.info('Merge product template %r into %s' % ((self.src_product_tmpl_ids - self.dst_product_tmpl_id).ids, self.dst_product_tmpl_id.id))

        PTAL = self.env['product.template.attribute.line'].sudo()
        PTAV = self.env['product.template.attribute.value'].sudo()

        all_ptal = PTAL
        used_ptav = PTAV
        all_ptav = PTAV

        # Merged values.

        for pwml in self.pwml_ids:
            for pwmav in pwml.pwmav_ids:
                merged_ptav_ids = pwmav.merged_ptav_ids - pwmav.ptav_id
                if merged_ptav_ids:
                    pwmav.ptav_id.merge_records(merged_ptav_ids)

        _logger.info('Attribute values merged')

        # Merge similar products.

        pwml_ids = self.pwml_ids
        while pwml_ids:
            pwml = pwml_ids[0]
            pwml_ids -= pwml
            if pwml.will_merge_pwml_ids:
                pwml_ids -= pwml.will_merge_pwml_ids
                src_products = pwml.will_merge_pwml_ids.mapped('product_id') - pwml.product_id
                if src_products:
                    pwml.product_id.merge_records(src_products)

        _logger.info('Similar variants merged')

        # Associate value if from merged values.

        for pwml in self.pwml_ids:
            for pwmav in pwml.pwmav_ids:
                if pwmav.merged_ptav_ids:
                    if not pwmav.ptav_id:
                        pwmav.ptav_id = pwmav.merged_ptav_ids[0]

        # Update variant attributes & values.

        products = self.env['product.product']
        for pwml in self.pwml_ids:
            product = pwml.product_id

            if product in products:
                continue

            products += product
            template = product.product_tmpl_id
            used_ptav += product.product_template_attribute_value_ids
            ptav = PTAV

            for pwmav in pwml.pwmav_ids:
                ptal_self = pwmav.pwma_id.ptal_id
                if ptal_self:
                    ptal_self.value_ids += pwmav.value_id
                else:
                    # Create ptal (product.template.attribute.line) on template.
                    ptal_self = PTAL.create({
                        'product_tmpl_id': template.id,
                        'attribute_id': pwmav.attribute_id.id, # 'create_variant': 'dynamic',
                        'value_ids': pwmav.value_id.ids
                    })
                    pwmav.pwma_id.ptal_id = ptal_self

                ptav_self = pwmav.ptav_id
                if not ptav_self:
                    # Create ptav (product.template.attribute.value) on ptal.
                    ptav_self = PTAV.create({
                        'attribute_line_id': ptal_self.id,
                        'product_attribute_value_id': pwmav.value_id.id,
                    })
                    pwmav.ptav_id = ptav_self

                ptav_self.attribute_line_id = ptal_self
                ptal_self.product_template_value_ids += ptav_self

                if ptal_self not in all_ptal:
                    all_ptal += ptal_self
                if ptav_self not in ptav:
                    ptav += ptav_self

            all_ptav += ptav

            # Update values on product.product.
            product.product_template_attribute_value_ids = ptav

        _logger.info('Product and product attribute values updated')

        # Remove useless attribute values.

        ptav_to_remove = (used_ptav - all_ptav).exists()
        if ptav_to_remove:
            ptav_to_remove.unlink()

        _logger.info('Useless product attribute values removed')

        # Move variants to the destination template before merge template and
        # compute the combination indices to avoid constraints.

        for product in products:
            product._compute_combination_indices()
            product.product_tmpl_id = self.dst_product_tmpl_id.id

        _logger.info('Variants product ID updated')

        # Merge product.

        if self.src_product_tmpl_ids - self.dst_product_tmpl_id:
            self.dst_product_tmpl_id.merge_records(self.src_product_tmpl_ids)

        _logger.info('Product merged')

        # Update values on product.template and trigger compute fields.

        self.dst_product_tmpl_id.attribute_line_ids = all_ptal

        _logger.info('Merge complete')

        # Log the merge action.

        self.dst_product_tmpl_id.message_post(body=_("Merge Product Wizard was used."))

        return {
            'name': _("Merge product template"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'res_model': 'product.template',
            'res_id': self.dst_product_tmpl_id.id,
        }


class ProductWizardMergeLine(models.TransientModel):
    _name = 'product.wizard.merge.line'
    _description = 'Merge Product Wizard Line'

    selected = fields.Boolean(string='Select', store=False)

    wizard_id = fields.Many2one('product.wizard.merge', string='Wizard', required=True, readonly=True, ondelete='cascade')
    name = fields.Char(string='(product ID, variant ID) Product name', compute='_compute_name', store=True)

    product_id = fields.Many2one('product.product', string='Variant', required=True, readonly=True, ondelete='cascade')

    pwmav_ids = fields.Many2many('product.wizard.merge.attribute.value', string='Characteristics/Values', relation='product_wizard_merge_line_attribute_value_rel',
        help="(product ID #ref) Attribute Value.\nSelect a value. Only one value per attributes line is allowed")
    available_pwmav_ids = fields.Many2many('product.wizard.merge.attribute.value', compute='_compute_available_pwmav_ids', string='Avalaible values')
    has_error = fields.Boolean(string='Onchange triggered', compute='_compute_available_pwmav_ids')

    will_merge_pwml_ids = fields.Many2many('product.wizard.merge.line', relation='product_wizard_merge_line_with_rel', column1="id1", column2="id2", string='Will merge')
    will_merge_pwml_2_ids = fields.Many2many(related="will_merge_pwml_ids", readonly=True)
    will_merge_pwml = fields.Char(string='Will merge with', compute="_compute_will_merge_pwml",
        help="If two (or more) variants have the same characteristics, these variants will be merged with each other.")

    @api.depends("product_id")
    def _compute_name(self):
        """ Update the name
        """
        for pwml in self:
            pwml.name = "(%s,%s) %s" % (pwml.product_id.product_tmpl_id.id, pwml.product_id.id, pwml.product_id.product_tmpl_id.name)

    @api.depends("will_merge_pwml_ids")
    def _compute_will_merge_pwml(self):
        """ Search and record if the product will be merge with an other.
        """
        for pwml in self:
            will_merge_pwml = []
            for pwml_merge in pwml.will_merge_pwml_ids:
                will_merge_pwml.append("(%s,%s)" % (pwml_merge.product_id.product_tmpl_id.id, pwml_merge.product_id.id))
            pwml.will_merge_pwml = ', '.join(will_merge_pwml)

    @api.depends("pwmav_ids", "wizard_id.pwma_ids", "wizard_id.pwma_ids.pwmav_ids")
    def _compute_available_pwmav_ids(self):
        """ Update the list of avalable values and mark as error if the product
            have not enough or too much attributes.
        """
        for line in self:
            pwmav_self = line.pwmav_ids.mapped("pwma_id")
            available_pwma = line.wizard_id.pwma_ids.filtered(lambda pwma: pwma._origin.id not in pwmav_self.ids)
            line.available_pwmav_ids = available_pwma.mapped("pwmav_ids")
            line.has_error = bool(line.available_pwmav_ids)
            if not line.has_error:
                pwma = self.env['product.wizard.merge.attribute']
                for value in line.available_pwmav_ids:
                    if value.pwma_id in pwma:
                        line.has_error = True
                    pwma += value.pwma_id


class ProductWizardMergeAttribute(models.TransientModel):
    _name = 'product.wizard.merge.attribute'
    _description = 'Merge Product Wizard Attribute'

    wizard_id = fields.Many2one('product.wizard.merge', string='Wizard', required=True, readonly=True, ondelete='cascade')
    name = fields.Char(string='(ref) Name', compute='_compute_name')
    attribute_id = fields.Many2one('product.attribute', string='Attribute', required=True, ondelete='cascade')
    pwmav_ids = fields.One2many('product.wizard.merge.attribute.value', 'pwma_id', string='Values',
        help="(product ID #ref) Attribute Value.\nSelect a value to move the value from a previous attribute. If the value already exists in the row, it will be merged with the one present.")
    previous_pwmav_ids = fields.Many2many('product.wizard.merge.attribute.value', compute="_compute_previous_pwmav_ids", inverse='_set_previous_pwmav_ids', store=False, string='Previous values')
    ptal_id = fields.Many2one('product.template.attribute.line', string='Existing value')
    product_tmpl_id = fields.Many2one(related="ptal_id.product_tmpl_id", string='Actually on the product')

    @api.depends("attribute_id")
    def _compute_name(self):
        """ Update the name
        """
        for pwma in self:
            pwma.name = "(%s #%s) %s" % (pwma.product_tmpl_id.id or '', pwma.id, pwma.attribute_id.name)

    @api.onchange("pwmav_ids")
    def _compute_previous_pwmav_ids(self):
        """ Set the default previous values field.
        """
        for pwma in self:
            if not pwma.previous_pwmav_ids:
                pwma.previous_pwmav_ids = pwma.pwmav_ids

    def _set_previous_pwmav_ids(self):
        """ Allow to add or remove values in the previous values field.
        """
        return


class ProductWizardMergeAttributeValue(models.TransientModel):
    _name = 'product.wizard.merge.attribute.value'
    _description = 'Merge Product Wizard Attribute Value'

    _order = 'pwma_id, name'

    name = fields.Char(string='(ref) Name', compute='_compute_name', store=True)
    wizard_id = fields.Many2one('product.wizard.merge', string='Wizard', required=True, ondelete='cascade')
    pwma_id = fields.Many2one('product.wizard.merge.attribute', string='Merge Attribute', required=True, ondelete='cascade')
    attribute_id = fields.Many2one(related='pwma_id.attribute_id', string='Attribute')
    value_id = fields.Many2one('product.attribute.value', string='Value', required=True, ondelete='cascade')
    ptav_id = fields.Many2one('product.template.attribute.value', string='Existing value')
    merged_ptav_ids = fields.Many2many('product.template.attribute.value', relation="product_wizard_merge_attribute_value_self_rel", column1="id1", column2="id2", string='To merge values')
    color = fields.Integer(string='Color', compute='_compute_color')

    @api.depends('ptav_id')
    def _compute_color(self):
        """ Use a color for values linked with existing product value.
        """
        for value in self:
            if value.ptav_id:
                value.color = 7  # green
            else:
                value.color = 0

    @api.depends("pwma_id", "attribute_id", "value_id")
    def _compute_name(self):
        """ Update the name
        """
        for value in self:
            value.name = "%s: %s" % (value.pwma_id.name, value.value_id.name)
