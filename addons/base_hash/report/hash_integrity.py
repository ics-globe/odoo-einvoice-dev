# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _, fields


class ReportHashIntegrity(models.AbstractModel):
    _name = 'report.base_hash.report_hash_integrity'
    _description = 'Get hash integrity result as PDF.'

    @staticmethod
    def _check_hash_integrity(is_checked, records, date_field=None):
        if not is_checked:
            return {
                'hash_verified': "False",
                'msg': _('The integrity check has not been verified.'),
            }

        if not records:
            return {
                'hash_verified': "False",
                'msg': _('There isn\'t any record flagged for data inalterability.'),
            }

        records = records.sorted("secure_sequence_number")
        corrupted_hash = None
        previous_hash = ''
        for record in records:
            if record.inalterable_hash != record._get_hash_string(previous_hash):
                corrupted_hash = record.id
                break
            previous_hash = record.inalterable_hash

        if corrupted_hash is not None:
            return {
                'hash_verified': "False",
                'msg': _('Corrupted data on record with id %s.', corrupted_hash),
            }

        date_field = date_field or 'date'

        return {
            'hash_verified': "True",
            'msg': 'None',
            'first_name': records[0]['name'],
            'first_hash': records[0]['inalterable_hash'],
            'first_date': fields.Date.to_string(records[0][date_field]),
            'last_name': records[-1]['name'],
            'last_hash': records[-1]['inalterable_hash'],
            'last_date': fields.Date.to_string(records[-1][date_field]),
        }
