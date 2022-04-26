# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields, _
from odoo.fields import Date
from odoo.tools import format_date
from odoo.addons.base_hash.report.hash_integrity import ReportHashIntegrity
from odoo.addons.base.models.ir_sequence import IrSequence


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    l10n_fr_pos_cert_sequence_id = fields.Many2one('ir.sequence', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies:
            #when creating a new french company, create the securisation sequence as well
            if company._is_accounting_unalterable():
                IrSequence._create_secure_sequence(company, "l10n_fr_pos_cert_sequence_id")
        return companies

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        #if country changed to fr, create the securisation sequence
        for company in self:
            if company._is_accounting_unalterable():
                IrSequence._create_secure_sequence(company, "l10n_fr_pos_cert_sequence_id")
        return res

    def _action_check_pos_hash_integrity(self):
        return self.env.ref('l10n_fr_pos_cert.action_report_pos_hash_integrity').report_action(self.id)

    def _check_pos_hash_integrity(self):
        orders = self.env['pos.order'].search(
            [('state', 'in', ['paid', 'done', 'invoiced']),
             ('company_id', '=', self.id),
             ('secure_sequence_number', '!=', 0)],
            order="secure_sequence_number ASC")
        return {
            'results': [ReportHashIntegrity._check_hash_integrity(self.env.company._is_accounting_unalterable(), orders, "date_order")],
            'printing_date': format_date(self.env, Date.to_string(Date.today()))
        }
