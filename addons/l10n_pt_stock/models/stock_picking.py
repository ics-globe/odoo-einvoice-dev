from odoo import models, api, fields
from odoo.addons.base.models.ir_sequence import IrSequence


class PickingType(models.Model):
    _name = 'stock.picking.type'
    _inherit = 'stock.picking.type'

    secure_sequence_id = fields.Many2one('ir.sequence',
        help='Sequence to use to ensure the securisation of data',
        readonly=True, copy=False)


class Picking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'hash.mixin']

    @api.depends('picking_type_id.code', 'picking_type_id.sequence_code', 'secure_sequence_number')
    def _compute_l10n_pt_document_no(self):
        for picking in self:
            if picking.company_id.country_id.code == 'PT':
                picking_type = picking.picking_type_id
                picking.l10n_pt_document_no = f'{picking_type.code} {picking_type.sequence_code}/{picking.secure_sequence_number}'
            else:
                picking.l10n_pt_document_no = ''

    @staticmethod
    def _get_fields_used_by_hash():
        return 'date_done', 'create_date', 'secure_sequence_number'

    @staticmethod
    def _get_sorting_key():
        return 'date_done'

    def _get_secure_sequence(self):
        self.ensure_one()
        IrSequence._create_secure_sequence(self.picking_type_id)
        return self.picking_type_id.secure_sequence_id

    def _get_previous_hash(self):
        self.ensure_one()
        prev_picking = self.search(
            [('state', '=', 'done'),
             ('id', '!=', self.id),
             ('picking_type_id.code', '=', 'outgoing'),
             ('secure_sequence_number', '<', self.secure_sequence_number),
             ('secure_sequence_number', '!=', 0),
             ('company_id', '=', self.company_id.id)],
            limit=1,
            order='secure_sequence_number DESC')
        return prev_picking.inalterable_hash if prev_picking else ""

    @api.depends('company_id.country_id.code', 'picking_type_id.code', 'date_done')
    def _compute_must_hash(self):
        for picking in self.sort_records(self):
            picking.must_hash = picking.company_id.country_id.code == 'PT' and \
                                       picking.picking_type_id.code == 'outgoing' and \
                                       picking.state == 'done' and \
                                       picking.date_done

    @api.depends('secure_sequence_number')
    def _compute_inalterable_hash(self):
        for picking in self.sorted("secure_sequence_number"):
            picking._l10n_pt_compute_inalterable_hash(picking.date_done, 0.0)
