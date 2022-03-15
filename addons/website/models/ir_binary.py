from odoo import models


class IrBinary(models.AbstractModel):
    _inherit = 'ir.binary'

    def _find_record(self, xmlid, *args, **kwargs):
        record = None
        if xmlid:
            website_id = self.env['website'].get_current_website()
            if website_id and website_id.theme_id:
                domain = [('key', '=', xmlid), ('website_id', '=', website_id.id)]
                Attachment = self.env['ir.attachment']
                if self.env.user.share:
                    domain.append(('public', '=', True))
                    Attachment = Attachment.sudo()
                record = Attachment.search(domain, limit=1)

        if not record:
            record = super()._find_record(xmlid, *args, **kwargs)

        if 'website_published' in record._fields and record.sudo().website_published:
            record = record.sudo()

        return record
