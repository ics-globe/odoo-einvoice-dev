# -*- coding: utf-8 -*-

from odoo import models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def _get_edi_attachments(self, document):
        """
        Will return the information about the attachment of the edi document for adding the attachment in the mail.
        Can be overridden where e.g. a zip-file needs to be sent with the individual files instead of the entire zip
        :param document: an edi document
        :return: list with a tuple with the name and base64 content of the attachment
        """
        if not document.attachment_id:
            return []
        return [(document.attachment_id.name, document.attachment_id.datas)]

    def _generate_template(self, res_ids, render_fields):
        res = super()._generate_template(res_ids, render_fields)

        if self.model not in ['account.move', 'account.payment']:
            return res

        records = self.env[self.model].browse(res_ids)
        for record in records:
            for doc in record.edi_document_ids:
                res[record.id].setdefault('attachments', [])
                res[record.id]['attachments'] += self._get_edi_attachments(doc)

        return res
