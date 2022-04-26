# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move']

    @api.depends('move_type', 'sequence_prefix', 'sequence_number')
    def _compute_l10n_pt_document_no(self):
        for move in self:
            if move.company_id.account_fiscal_country_id.code == 'PT':
                move.l10n_pt_document_no = f"{move.move_type} {move.sequence_prefix.replace('/', '.', 1)}{str(move.sequence_number)}"
            else:
                move.l10n_pt_document_no = ''

    def _get_previous_hash(self):
        """ Returns the hash to write on Portuguese sales and purchases when they get posted"""
        self.ensure_one()

        if self.company_id.account_fiscal_country_id.code != 'PT':
            return super()._get_previous_hash()

        # We should only hash invoices and refunds
        if self.move_type not in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
            return ""

        # Get the only one exact previous move in the securisation sequence
        prev_move = self.search(
            [('state', '=', 'posted'),
             ('move_type', '=', self.move_type),
             ('company_id', '=', self.company_id.id),
             ('id', '!=', self.id),
             ('secure_sequence_number', '<', self.secure_sequence_number),
             ('secure_sequence_number', '!=', 0)],
            limit=1,
            order='secure_sequence_number DESC')
        return prev_move.inalterable_hash if prev_move else ""

    @staticmethod
    def _get_fields_used_by_hash():
        return 'invoice_date', 'create_date', 'amount_total'

    def _get_hash_string(self, previous_hash=None):
        """ Returns the string that is used in the securisation """
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code == 'PT':
            return self._l10n_pt_get_hash_string(self.invoice_date, self.amount_total, previous_hash)
        return super()._get_hash_string()

    def _compute_inalterable_hash(self):
        for move in self.sorted("secure_sequence_number"):
            if move.company_id.account_fiscal_country_id.code == 'PT':
                move._l10n_pt_compute_inalterable_hash(move.invoice_date, move.amount_total)
            else:
                super()._compute_inalterable_hash()
