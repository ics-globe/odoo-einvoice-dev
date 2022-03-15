# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import functools
import io
import json
import logging
import os
import unicodedata

import odoo
import odoo.modules.registry
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.modules import get_resource_path
from odoo.tools import pycompat
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.misc import file_open, file_path
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)

BAD_X_SENDFILE_WARNING = """\
Odoo is running with --x-sendfile. It means nginx should be serving the
/web/filesystem route however Odoo is receiving the request. Is nginx
correctly configured? Is Odoo only accessible through nginx? Does the
requested file's permissions allow nginx to read it?

Make sure the /web/filesystem location block exists and contains a
configuration similar to:

    location /web/filesystem {
        internal;
        alias /;
    }
"""


def clean(name):
    return name.replace('\x3c', '')


class Binary(http.Controller):

    @http.route('/web/filesystem/<path:_path>', type='http', auth='none')
    def content_filesystem(self, _path):
        if odoo.tools.config['x_sendfile']:
            _logger.warning(BAD_X_SENDFILE_WARNING)
        raise http.request.not_found()

    @http.route(['/web/content',
        '/web/content/<string:xmlid>',
        '/web/content/<string:xmlid>/<string:filename>',
        '/web/content/<int:res_id>',
        '/web/content/<int:res_id>/<string:filename>',
        '/web/content/<string:model>/<int:res_id>/<string:field>',
        '/web/content/<string:model>/<int:res_id>/<string:field>/<string:filename>'], type='http', auth="public")
    def content_common(self, xmlid=None, model='ir.attachment', res_id=None, field='raw',
                       filename=None, filename_field='name', mimetype=None,
                       download=False, token=None, access_token=None, **kw):
        record = request.env['ir.binary']._find_record(xmlid, model, res_id, access_token)
        stream = request.env['ir.binary']._get_stream_from(record, field, filename, filename_field, mimetype)
        return stream.get_response(as_attachment=download)

    @http.route(['/web/assets/debug/<string:filename>',
        '/web/assets/debug/<path:extra>/<string:filename>',
        '/web/assets/<int:res_id>/<string:filename>',
        '/web/assets/<int:res_id>/<path:extra>/<string:filename>'], type='http', auth="public")
    def content_assets(self, res_id=None, filename=None, extra=None, **kw):
        if not id:
            domain = [('url', '=like', '/web/assets/%/' + ('{extra}/{filename}' if extra else filename))]
            res_id = request.env['ir.attachment'].sudo().search_read(domain, fields=['id'], limit=1)[0]['id']
        record = request.env['ir.binary']._find_record(res_id=res_id)
        stream = request.env['ir.binary']._get_stream_from(record, 'raw', filename)
        return stream.get_response(as_attachment=False)

    @http.route(['/web/image',
        '/web/image/<string:xmlid>',
        '/web/image/<string:xmlid>/<string:filename>',
        '/web/image/<string:xmlid>/<int:width>x<int:height>',
        '/web/image/<string:xmlid>/<int:width>x<int:height>/<string:filename>',
        '/web/image/<string:model>/<int:res_id>/<string:field>',
        '/web/image/<string:model>/<int:res_id>/<string:field>/<string:filename>',
        '/web/image/<string:model>/<int:res_id>/<string:field>/<int:width>x<int:height>',
        '/web/image/<string:model>/<int:res_id>/<string:field>/<int:width>x<int:height>/<string:filename>',
        '/web/image/<int:res_id>',
        '/web/image/<int:res_id>/<string:filename>',
        '/web/image/<int:res_id>/<int:width>x<int:height>',
        '/web/image/<int:res_id>/<int:width>x<int:height>/<string:filename>'], type='http', auth="public")
    def content_image(self, xmlid=None, model='ir.attachment', res_id=None, field='raw',
                      filename_field='name', filename=None, mimetype=None,
                      download=False, width=0, height=0, crop=False, access_token=None):
        record = request.env['ir.binary']._find_record(xmlid, model, res_id, access_token)
        stream = request.env['ir.binary']._get_image_stream_from(
            record, field, filename=filename, filename_field=filename_field,
            mimetype=mimetype, width=width, height=height, crop=crop,
        )
        return stream.get_response(as_attachment=download)

    @http.route('/web/binary/upload_attachment', type='http', auth="user")
    def upload_attachment(self, model, id, ufile, callback=None):
        files = request.httprequest.files.getlist('ufile')
        Model = request.env['ir.attachment']
        out = """<script language="javascript" type="text/javascript">
                    var win = window.top.window;
                    win.jQuery(win).trigger(%s, %s);
                </script>"""
        args = []
        for ufile in files:

            filename = ufile.filename
            if request.httprequest.user_agent.browser == 'safari':
                # Safari sends NFD UTF-8 (where é is composed by 'e' and [accent])
                # we need to send it the same stuff, otherwise it'll fail
                filename = unicodedata.normalize('NFD', ufile.filename)

            try:
                attachment = Model.create({
                    'name': filename,
                    'datas': base64.encodebytes(ufile.read()),
                    'res_model': model,
                    'res_id': int(id)
                })
                attachment._post_add_create()
            except AccessError:
                args.append({'error': _("You are not allowed to upload an attachment here.")})
            except Exception:
                args.append({'error': _("Something horrible happened")})
                _logger.exception("Fail to upload attachment %s", ufile.filename)
            else:
                args.append({
                    'filename': clean(filename),
                    'mimetype': ufile.content_type,
                    'id': attachment.id,
                    'size': attachment.file_size
                })
        return out % (json.dumps(clean(callback)), json.dumps(args)) if callback else json.dumps(args)

    @http.route([
        '/web/binary/company_logo',
        '/logo',
        '/logo.png',
    ], type='http', auth="none", cors="*")
    def company_logo(self, dbname=None, **kw):
        imgname = 'logo'
        imgext = '.png'
        placeholder = functools.partial(get_resource_path, 'web', 'static', 'img')
        dbname = request.db
        uid = (request.session.uid if dbname else None) or odoo.SUPERUSER_ID

        if not dbname:
            response = http.send_file(placeholder(imgname + imgext))
        else:
            try:
                # create an empty registry
                registry = odoo.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    company = int(kw['company']) if kw and kw.get('company') else False
                    if company:
                        cr.execute("""SELECT logo_web, write_date
                                        FROM res_company
                                       WHERE id = %s
                                   """, (company,))
                    else:
                        cr.execute("""SELECT c.logo_web, c.write_date
                                        FROM res_users u
                                   LEFT JOIN res_company c
                                          ON c.id = u.company_id
                                       WHERE u.id = %s
                                   """, (uid,))
                    row = cr.fetchone()
                    if row and row[0]:
                        image_base64 = base64.b64decode(row[0])
                        image_data = io.BytesIO(image_base64)
                        mimetype = guess_mimetype(image_base64, default='image/png')
                        imgext = '.' + mimetype.split('/')[1]
                        if imgext == '.svg+xml':
                            imgext = '.svg'
                        response = http.send_file(image_data, filename=imgname + imgext, mimetype=mimetype, mtime=row[1])
                    else:
                        response = http.send_file(placeholder('nologo.png'))
            except Exception:
                response = http.send_file(placeholder(imgname + imgext))

        return response

    @http.route(['/web/sign/get_fonts', '/web/sign/get_fonts/<string:fontname>'], type='json', auth='public')
    def get_fonts(self, fontname=None):
        """This route will return a list of base64 encoded fonts.

        Those fonts will be proposed to the user when creating a signature
        using mode 'auto'.

        :return: base64 encoded fonts
        :rtype: list
        """
        supported_exts = ('.ttf', '.otf', '.woff', '.woff2')
        fonts = []
        fonts_directory = file_path(os.path.join('web', 'static', 'fonts', 'sign'))
        if fontname:
            font_path = os.path.join(fonts_directory, fontname)
            with file_open(font_path, 'rb', filter_ext=supported_exts) as font_file:
                font = base64.b64encode(font_file.read())
                fonts.append(font)
        else:
            font_filenames = sorted([fn for fn in os.listdir(fonts_directory) if fn.endswith(supported_exts)])
            for filename in font_filenames:
                font_file = file_open(os.path.join(fonts_directory, filename), 'rb', filter_ext=supported_exts)
                font = base64.b64encode(font_file.read())
                fonts.append(font)
        return fonts
