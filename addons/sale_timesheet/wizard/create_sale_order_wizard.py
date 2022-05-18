# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError


class CreateSaleOrderWizard(models.TransientModel):
    _name = 'create.sale.order.wizard'
    _description = 'Create Sale Order from project, task, timesheet or another record'

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        active_model = self._context.get('active_model', '')
        if active_model not in self.env['create.sale.order.reference.wizard']._get_document_models():
            raise UserError(_('You cannot apply this action with this current model.'))
        active_ids = self._context.get('active_ids', [self._context['active_id']])  # if no active_ids then active_id must be defined
        sale_line_field = self._get_sale_order_item_field_per_model(active_model)
        records = self.env[active_model] \
            .browse(active_ids) \
            .filtered(lambda rec: not rec[sale_line_field] and rec.partner_id)
        if not records:
            raise UserError('There are no sales orders to create.')
        sale_order = self.env['sale.order']
        if active_model == 'project.project':
            sale_order = records.sale_order_id
            result['project_id'] = records.id
        else:
            sale_order = records.project_id.sale_order_id
            if len(records.project_id) == 1:
                result['project_id'] = records.project_id.id
        if sale_order:
            raise UserError(_("The project has already a sale order."))
        result['reference_ids'] = [
            Command.create({'res_model': active_model, 'res_id': rec.id})
            for rec in records
        ]
        return result

    project_id = fields.Many2one('project.project', 'Project', readonly=True)
    timesheet_product_id = fields.Many2one('product.product', 'Default Service',
        required=True,
        default=lambda self: self.env.ref('sale_timesheet.time_product', False),
        domain="""[
            ('detailed_type', '=', 'service'),
            ('invoice_policy', '=', 'delivery'),
            ('service_type', '=', 'timesheet'),
            '|', ('company_id', '=', False), ('company_id', '=', company_id)]""")
    reference_ids = fields.One2many('create.sale.order.reference.wizard', 'wizard_id', 'Related Documents')
    line_ids = fields.One2many('create.sale.order.line.wizard', 'wizard_id', 'Lines')

    def action_create_sale_order(self):
        sale_orders = self._create_sale_orders()
        sale_order_action = {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "name": "Sales Orders",
            "context": {"create": False, "show_sale": True},
            "domain": [('id', 'in', sale_orders.ids)],
            "views": [[False, "tree"], [False, "kanban"], [False, "calendar"], [False, "pivot"],
                      [False, "graph"], [False, "activity"], [False, "form"]],
        }
        if len(sale_orders) == 1:
            sale_order_action.update({
                "res_id": sale_orders.id,
                "views": [[False, "form"]],
            })
        return sale_order_action

    def _get_sale_order_item_field_per_model_dict(self):
        return {
            'project.project': 'sale_line_id',
            'project.task': 'sale_line_id',
            'account.analytic.line': 'so_line',
        }

    def _get_sale_order_item_field_per_model(self, model):
        sale_order_item_field_per_model_dict = self._get_sale_order_item_field_per_model_dict()
        assert model in sale_order_item_field_per_model_dict
        return sale_order_item_field_per_model_dict[model]

    def _create_sale_orders(self):
        if self.project_id.sale_line_id:
            raise UserError(_('The project is already linked to a sales order item.'))
        if not self.reference_ids:
            raise UserError(_('At least, one document should be linked to this wizard to create a sale order.'))
        sale_order_vals_list = []
        if self.project_id:
            sale_order_vals_list.append(self._get_default_sale_order_vals())
        else:
            sale_order_vals_list = [
                self._get_default_sale_order_vals(project)
                for project in self.reference_ids.resource_ref.project_id
            ]
        sale_orders = self.env['sale.order'].create(sale_order_vals_list)
        sale_order_items = self._create_sale_order_items(sale_orders)
        sale_orders.action_confirm()
        if self.line_ids.employee_id:
            self._create_employee_mappings(sale_order_items)
        self._link_sale_order_items_to_references(sale_order_items)
        return sale_orders

    def _get_default_sale_order_vals(self, project=None):
        if not project:
            project = self.project_id
        assert project
        return {
            'project_id': project.id,
            'partner_id': project.partner_id.id,
            'analytic_account_id': project.analytic_account_id.id,
            'client_order_ref': project.name,
            'company_id': project.company_id.id,
        }

    def _create_sale_order_items(self, sale_orders):
        task_ids_per_project_id = defaultdict(list)
        for task in self.reference_ids._get_tasks():
            task_ids_per_project_id[task.project_id.id].append(task.id)
        sale_items_vals_list = []
        for so in sale_orders:
            price_units_per_product = defaultdict(list)
            sale_items_vals_list.append({
                'order_id': so.id,
                'product_id': self.timesheet_product_id.id,
                'project_id': so.project_id.id,
            })
            for line in self.line_ids:
                price_units_per_product[line.product_id].append(line.price_unit)
            for product, price_unit_list in price_units_per_product.items():
                for price_unit in price_unit_list:
                    sale_items_vals_list.append({
                        'order_id': so.id,
                        'product_id': product.id,
                        'price_unit': price_unit,
                        'project_id': so.project_id.id,
                        'product_uom_qty': 0.0,
                    })
        sale_order_items = self.env['sale.order.line'].with_context(sale_project_task_generation=False).create(sale_items_vals_list)
        return sale_order_items

    def _create_employee_mappings(self, sale_order_items):
        projects = self.project_id or self.reference_ids.resource_ref.project_id
        sale_order_item_ids_per_project_id = defaultdict(list)
        for sol in sale_order_items:
            sale_order_item_ids_per_project_id[sol.project_id.id].append(sol.id)
        employee_mapping_vals_list = []
        for project in projects:
            sale_items = self.env['sale.order.line'].browse(sale_order_item_ids_per_project_id.get(project.id, []))
            sale_item_id_per_product_and_unit_price = {(sol.product_id.id, sol.price_unit): sol.id for sol in sale_items}
            for line in self.line_ids:
                if not line.employee_id:  # then no employee mapping to generate with this line
                    continue
                sale_line_id = sale_item_id_per_product_and_unit_price.get((line.product_id.id, line.price_unit), False)
                if not sale_line_id:  # normally this case should never happen.
                    continue
                employee_mapping_vals_list.append({
                    'employee_id': line.employee_id.id,
                    'project_id': project.id,
                    'price_unit': line.price_unit,
                    'sale_line_id': sale_line_id,
                })
        self.env['project.sale.line.employee.map'].create(employee_mapping_vals_list)

    def _link_sale_order_items_to_references(self, sale_order_items):
        model = self.reference_ids[0].res_model
        if model == 'project.project':
            self.project_id.sale_line_id = sale_order_items.filtered(lambda sol: sol.product_id == self.timesheet_product_id)[:1]
            return
        elif model == 'account.analytic.line':  # the so_line should automatically set with `_compute_so_line` method
            return
        sol_ids_per_project = defaultdict(list)
        for sol in sale_order_items:
            sol_ids_per_project[(sol.project_id.id, sol.task_id.id)].append(sol.id)
        for ref in self.reference_ids:
            sale_line_ids = sol_ids_per_project.get((ref.resource_ref.project_id.id, ref._get_tasks().id), [])
            if not sale_line_ids:
                continue
            vals = {} if model != 'account.analytic.line' else {'is_so_line_manually_edited': True}
            ref.resource_ref.write({
                self._get_sale_order_item_field_per_model(model): sale_line_ids[-1],
                **vals,
            })


class CreateSaleOrderReferenceWizard(models.TransientModel):
    _name = 'create.sale.order.reference.wizard'
    _description = 'Reference records linked to the Create Sale Order Wizard'

    def _get_document_models(self):
        return ['account.analytic.line', 'project.project', 'project.task']

    @api.model
    def _selection_target_model(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([('model', 'in', self._get_document_models())])]

    wizard_id = fields.Many2one('create.sale.order.wizard', required=True)
    res_model = fields.Char('Related Document Model', required=True)
    res_id = fields.Integer('Related Document ID', required=True)
    resource_ref = fields.Reference('_selection_target_model', 'Related Document', compute='_compute_resource_ref')

    @api.depends('res_model', 'res_id')
    def _compute_resource_ref(self):
        for wizard in self:
            if wizard.res_model and wizard.res_model in self.env:
                wizard.resource_ref = '%s,%s' % (wizard.res_model, wizard.res_id or 0)
            else:
                wizard.resource_ref = None

    def _get_tasks(self):
        model = self[0].res_model
        if model == 'project.task':
            return self.resource_ref
        elif model == 'project.project':
            return self.resource_ref.task_ids
        elif model == 'account.analytic.line':
            return self.resource_ref.task_id
        return self.env['project.task']

    def _get_timesheet_field_per_model(self):
        return {
            'project.project': 'project_id',
            'project.task': 'task_id',
            'account.analytic.line': 'id',
        }

    def _get_unit_amount_per_employee(self):
        model = self[0].res_model
        timesheet_field_per_model = self._get_timesheet_field_per_model()
        domain = [('project_id', '!=', False), (timesheet_field_per_model[model], 'in', self.mapped('res_id'))]
        timesheet_read_group = self.env['account.analytic.line']._read_group(
            domain,
            ['project_id', 'employee_id', 'unit_amount'],
            ['project_id', 'employee_id'],
            lazy=False,
        )
        unit_amount_per_employee_id_per_project_id = defaultdict(dict)
        for res in timesheet_read_group:
            employee_id = res['employee_id'] and res['employee_id'][0]
            unit_amount_per_employee_id_per_project_id[res['project_id'][0]][employee_id] = res['unit_amount']
        return unit_amount_per_employee_id_per_project_id


class CreateSaleOrderEmployeeMappingWizard(models.TransientModel):
    _name = 'create.sale.order.line.wizard'
    _description = 'Employee Mappings for Create Sale Order Wizard'

    wizard_id = fields.Many2one('create.sale.order.wizard', required=True)
    employee_id = fields.Many2one('hr.employee', required=True)
    product_id = fields.Many2one('product.product', 'Service',
        domain="""[
            ('detailed_type', '=', 'service'),
            ('invoice_policy', '=', 'delivery'),
            ('service_type', '=', 'timesheet'),
            '|', ('company_id', '=', False), ('company_id', '=', company_id)]""")
    price_unit = fields.Float('Unit Price', compute='_compute_price_unit', store=True, readonly=False)
    currency_id = fields.Many2one(related='product_id.currency_id')

    _sql_constraints = [
        ('unique_employee_product', 'UNIQUE(employee_id, product_id)', 'Only a product should be defined to an employee or as a default product.'),
    ]

    @api.depends('product_id')
    def _compute_price_unit(self):
        for line in self:
            if line.product_id:
                line.price_unit = line.product_id.lst_price
