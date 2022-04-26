from hashlib import sha256
from json import dumps

from odoo import fields, models, _, api
from odoo.exceptions import UserError


class HashMixin(models.AbstractModel):
    """
    This mixin can be inherited by models that need a chained hashing system.
    """
    _name = 'hash.mixin'
    _description = "Hash Mixin"

    must_hash = fields.Boolean(compute='_compute_must_hash')
    secure_sequence_number = fields.Integer(string='Inalteralbility No Gap Sequence #',
                                            compute='_compute_secure_sequence_number',
                                            store=True, readonly=True, copy=False)
    inalterable_hash = fields.Char(string='Inalterability Hash',
                                   compute='_compute_inalterable_hash',
                                   store=True, readonly=True, copy=False)

    def _compute_must_hash(self):
        """
        This method must be overriden by the inheriting class.
        It should return True if the record must be hashed (depending on some record fields), False otherwise.
        """
        raise NotImplementedError("'_compute_must_hash' must be overriden by the inheriting class")

    def _get_secure_sequence(self):
        """
        This method must be overriden by the inheriting class.
        It should return sequence to which this record belong.
        This record will be have a number (secure_sequence_number) which is a
        link in the chain (secure_sequence).
        E.g.: account.move is a link (i.e. has a secure_sequence_number) in the
        chain of account.journal (i.e. has a secure_sequence).
        """
        raise NotImplementedError("'_get_secure_sequence' must be overriden by the inheriting class")

    def _get_sorting_key(self):
        """
        This method must be overriden by the inheriting class.
        It should return the key on which the records will be sorted.
        E.g.: 'invoice_date'
        """
        raise NotImplementedError("'_get_sort_keys' must be overriden by the inheriting class")

    def _get_previous_hash(self):
        """
        This method must be overriden by the inheriting class.
        It should return the hash of the previous record in the secure_sequence chain.
        This previous hash is going to be used to compute the new hash of the current record
        to create an inalterable hash chain.
        """
        raise NotImplementedError("'_get_previous_hash' must be overriden by the inheriting class")

    def _get_fields_used_by_hash(self):
        """
        This method must be overriden by the inheriting class.
        It should return a list of fields used by the hash. This means that once the inalterable
        hash is computed, we will no longer be able to modify these fields because otherwise the
        newly computed hash would be different and
        E.g.: ['create_date', 'done_date', 'name']
        """
        raise NotImplementedError("'_get_fields_used_by_hash' must be overriden by the inheriting class"
                                  "that uses the following '_get_hash_string' method")

    @staticmethod
    def sort_records(records):
        """
        This method sorts the given records according to the _get_sorting_key method.
        For this we create a tuple which allows us to sort by 3 values:
        - The first value is whether the value of the record[key] exists or not.
            (so that we can put those record[key]=False at the end)
        - The second value is the sorting key
        - The third value is the id of the record
            (whenever two records have the same sorting key, we want the one with the smallest id to appear first)
        """
        return records.sorted(key=lambda r: (r[r._get_sorting_key()] is False,
                                             r[r._get_sorting_key()],
                                             r['id']))

    @api.depends('must_hash')
    def _compute_secure_sequence_number(self):
        for record in self.sort_records(self):
            if not record.secure_sequence_number and record.must_hash:
                record.secure_sequence_number = record._get_secure_sequence().next_by_id()
            else:
                record.secure_sequence_number = record.secure_sequence_number or False

    @api.depends('secure_sequence_number')
    def _compute_inalterable_hash(self):
        """ Computes the hash of the browse_record given as self, based on the hash
        of the previous record in the company's securisation sequence"""
        for record in self.sorted("secure_sequence_number"):
            if not record.inalterable_hash and record.must_hash:
                record.inalterable_hash = record._get_hash_string()
            else:
                record.inalterable_hash = record.inalterable_hash or False

    @staticmethod
    def _get_field_value(obj, attr):
        # Get the value of a field of an object as a string
        # Field might be simple or simple of recordset
        # E.g.: _get_field_value(account.move(1), 'name') => 'Invoice INV/2022/00001'
        # E.g.: _get_field_value(account.move(1), 'line_ids.debit') => '123.00;4567.89;1000.00'
        value = ""
        if '.' in attr:
            sub_obj, sub_field = attr.split('.', 1)
            value += HashMixin._get_field_value(obj[sub_obj], sub_field)
        else:
            sub_values = ""
            for elem in obj:
                val = elem[attr]
                if elem._fields[attr].type == 'many2one':
                    val = val.id
                if elem._fields[attr].type in ['many2many', 'one2many']:
                    val = elem[attr].sorted().ids
                sub_values += str(val) + ';'
            value += sub_values
        return value

    def _get_hash_string(self, previous_hash=None):
        """
        Returns the hash as a string computed with the previous hash and the fields in self._get_fields_used_by_hash
        """
        self.ensure_one()
        # Make the json serialization canonical https://tools.ietf.org/html/draft-staykov-hu-json-canonical-form-00)
        hash_string = dumps(
            {field: HashMixin._get_field_value(self, field) for field in self._get_fields_used_by_hash()},
            sort_keys=True,
            ensure_ascii=True,
            indent=None,
            separators=(',', ':')
        )
        if previous_hash is None:
            previous_hash = self._get_previous_hash()
        hash_string = sha256((previous_hash + hash_string).encode('utf-8'))
        return hash_string.hexdigest()

    def write(self, vals):
        for record in self:
            if record.must_hash and record.inalterable_hash and set(vals).intersection(record._get_fields_used_by_hash()):
                raise UserError(_("You cannot edit the following fields due to restrict mode being activated on the parent: %s.") % ', '.join(record._get_fields_used_by_hash()))
            if 'inalterable_hash' in vals and record.inalterable_hash:
                raise UserError(_("You cannot modify the inalterable hash of a document."))
        return super().write(vals)


class SubHashMixin(models.AbstractModel):
    """
    This mixin is used for models which are themselves used in another model which is hashed.
    This mixin must be inherited by models whose fields are used in the HashMixin_get_fields_used_by_hash.
    E.g.:
    ModelA has fields: field_a, field_b, field_c
    ModelB has fields: field_d, field_e, modelA_id
    ModelA._get_fields_used_by_hash() returns ['field_a', 'field_b']
    ModelB._get_fields_used_by_hash() returns ['field_d', 'modelA_id']
    ModelB will call modelA_id._get_fields_used_by_hash() to get the sub-fields that must be hashed too.
    Then, via this SubHashMixin, we are able to check that the fields ['field_a', 'field_b'] of ModelA are
    not modified while the HashMixin used by ModelB will check that the fields ['field_d'] are not modified.
    """
    _name = 'sub.hash.mixin'
    _description = "Sub Hash Mixin"

    def _get_hash_parent(self):
        """
        This method must be overriden by the inheriting class.
        It should return the parent record of the current record.
        Represents the parent field who inherits from hash.mixin
        """
        raise NotImplementedError("'get_parent' must be overriden by the inheriting class")

    def _get_fields_used_by_hash(self):
        """E.g.: 'create_date', 'debit', 'done_date' """
        raise NotImplementedError("'_get_fields_used_by_hash' must be overriden by the inheriting class")

    def write(self, vals):
        for record in self:
            if record._get_hash_parent().must_hash and record._get_hash_parent().inalterable_hash and set(vals).intersection(record._get_fields_used_by_hash()):
                raise UserError(_("You cannot edit the following fields due to restrict mode being activated on the parent: %s.") % ', '.join(record._get_fields_used_by_hash()))
        return super().write(vals)
