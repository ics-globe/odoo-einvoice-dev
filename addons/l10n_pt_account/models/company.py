from odoo import models, fields
from odoo.tools import format_date
from odoo.addons.base_hash.report.hash_integrity import ReportHashIntegrity


class ResCompany(models.Model):
    _name = "res.company"
    _inherit = "res.company"

    def _check_journals_hash_integrity(self):
        if self.country_id.code != 'PT':
            return super()._check_journals_hash_integrity()
        results = {
            'results': [],
            'printing_date': format_date(self.env, fields.Date.to_string(fields.Date.context_today(self)))
        }
        for move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
            moves = self.env['account.move'].search(
                [('state', '=', 'posted'),
                 ('move_type', '=', move_type),
                 ('company_id', '=', self.id)],
                order="secure_sequence_number ASC")
            move_type_check = ReportHashIntegrity._check_hash_integrity(True, moves)
            move_type_check['journal_name'] = dict(moves._fields['move_type'].selection)[move_type]
            move_type_check['journal_code'] = move_type
            move_type_check['restricted_by_hash_table'] = 'V'
            if move_type_check['msg'] == 'None':
                move_type_check['msg'] = 'All entries are hashed.'
            results['results'].append(move_type_check)
        return results
