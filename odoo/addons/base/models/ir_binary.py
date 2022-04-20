import logging
import os.path
from datetime import datetime
from mimetypes import guess_extension
from werkzeug.http import is_resource_modified

from odoo import models
from odoo.exceptions import MissingError
from odoo.http import Stream, request
from odoo.tools import image_process, file_open
from odoo.tools.mimetypes import guess_mimetype


_logger = logging.getLogger(__name__)
DEFAULT_PLACEHOLDER = 'web/static/img/placeholder.png'


class IrBinary(models.AbstractModel):
    _name = 'ir.binary'
    _description = "File streaming helper model"

    def _find_record(self, xmlid=None, model='ir.attachment', res_id=None, access_token=None):
        record = None
        if xmlid:
            record = self.env.ref(xmlid)
        elif res_id is not None and model in self.env:
            record = self.env[model].browse(res_id)
        if not record or not record.exists():
            raise MissingError(f"No record found for xmlid={xmlid} or (model={model}, id={res_id})")

        if record._name == 'ir.attachment':
            record = record.validate_access(access_token)

        # We have prefetched some fields of record, among which the field
        # 'write_date' used by '__last_update' below. In order to check
        # access on record, we have to invalidate its cache first.
        if not record.env.su:
            record._cache.clear()
        record['__last_update']  # it checks accesses

        return record

    def _get_stream_from(
        self, record, field='raw', filename=None, filename_field='name',
        mimetype=None, default_mimetype='application/octet-stream',
        placeholder=None
    ):
        # 'web/static/img/placeholder.png'
        record.ensure_one()

        field_def = record._fields[field]
        if field_def.type != 'binary':
            raise TypeError(f"Field '{field_def!r}' is type {field_def.type!r} but it is only possible to stream 'binary' fields.")
        elif record._name == 'ir.attachment':
            stream = Stream.from_attachment(record)
        elif not field_def.attachment or field_def.compute or field_def.related:
            stream = Stream.from_binary_field(record, field)
        else:
            field_attachment = self.env['ir.attachment'].sudo().search(
                domain=[('res_model', '=', record._name),
                        ('res_id', '=', record.id),
                        ('res_field', '=', field)],
                # fields=['name', 'raw', 'mimetype', 'checksum'],
                limit=1
            )
            if not field_attachment.exists():
                raise MissingError("The related attachment does not exist.")
            stream = Stream.from_attachment(field_attachment)

        if stream.type in ('data', 'path'):
            if not stream.size and placeholder:
                stream = Stream.from_path(placeholder)

            if mimetype:
                stream.mimetype = mimetype
            elif not stream.mimetype:
                if stream.type == 'data':
                    head = stream.data[:1024]
                else:
                    with open(stream.path, 'rb') as file:
                        head = file.read(1024)
                stream.mimetype = guess_mimetype(head, default=default_mimetype)

            if filename:
                stream.download_name = filename
            elif filename_field:
                stream.download_name = record[filename_field]
            if not stream.download_name:
                stream.download_name = f'{record._table}-{record.res_id}-{field}'

            if not os.path.splitext(stream.download_name)[1]:  # missing file extension
                stream.download_name += guess_extension(stream.mimetype) or ''

        return stream

    def _get_image_stream_from(
        self, record, field='raw', filename=None, filename_field='name',
        mimetype=None, default_mimetype='application/octet-stream',
        placeholder=True,
        width=0, height=0, crop=False, quality=0,
    ):
        if placeholder is True:
            placeholder = DEFAULT_PLACEHOLDER
        elif placeholder is False:
            placeholder = None

        stream = self._get_stream_from(record, field, filename, filename_field, mimetype, placeholder)

        # Compat for is_resource_modified
        if isinstance(stream.last_modified, (int, float)):
            stream.last_modified = datetime.utcfromtimestamp(stream.last_modified)

        # Cache aware resize
        stream.etag = f'{stream.etag}-{width}x{height}-crop={crop}-quality={quality}'
        if is_resource_modified(request.httprequest.environ, etag=stream.etag, last_modified=stream.last_modified):
            if width or height or crop:
                if stream.type == 'url':
                    raise NotImplementedError('Cannot resize an external image.')
                if stream.type == 'path':
                    with open(stream.path, 'rb') as file:
                        stream.type = 'data'
                        stream.path = None
                        stream.data = file.read()
                stream.data = image_process(stream.data, size=(width, height), crop=crop, quality=quality)
                stream.size = len(stream.data)

        return stream

    def _get_placeholder(self, path=False):
        if not path:
            path = DEFAULT_PLACEHOLDER
        with file_open(path, 'rb', filter_ext=('.png', '.jpg')) as file:
            return file.read()
