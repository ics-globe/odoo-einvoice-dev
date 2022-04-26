# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import float_repr


class L10nPtMixin(models.AbstractModel):
    _inherit = 'hash.mixin'
    _description = "Portugal Mixin - Contains common things between Portuguese apps"

    l10n_pt_document_no = fields.Char(string='DocumentNo', compute='_compute_l10n_pt_document_no', store=False)

    def _compute_l10n_pt_document_no(self):
        raise NotImplementedError("'_compute_l10n_pt_document_no' must be overriden by the inheriting class"
                                  "that uses the following '_l10n_pt_compute_inalterable_hash' method")

    def _l10n_pt_compute_inalterable_hash(self, date, gross_total, previous_hash=None):
        self.ensure_one()
        if not self.inalterable_hash and self.must_hash:
            self.inalterable_hash = self._l10n_pt_get_hash_string(date, gross_total, previous_hash)
        else:
            self.inalterable_hash = self.inalterable_hash or False

    def _l10n_pt_get_hash_string(self, date, gross_total, previous_hash=None):
        self.ensure_one()
        date = date.strftime('%Y-%m-%d')
        system_entry_date = self.create_date.strftime("%Y-%m-%dT%H:%M:%S")
        gross_total = float_repr(gross_total, 2)
        if previous_hash is None:
            previous_hash = self._get_previous_hash()
        message = f"{date};{system_entry_date};{self.l10n_pt_document_no};{gross_total};{previous_hash}"
        return self._l10n_pt_get_hashed_message(message)

    def _l10n_pt_get_hashed_message(self, message):
        """
        This method's purpose is only to test that the hash is correctly
        computed as we have multilple hash chains: one per move_type.
        In each chain, we simply add one 1 to the previous hash value of that chain.
        This method will be overriden in SaaS which will provide the real hash
        """
        self.ensure_one()
        hash_string = int(message[message.rfind(';')+1:]) + 1 if message[-1].isdigit() else 0
        return str(hash_string)
