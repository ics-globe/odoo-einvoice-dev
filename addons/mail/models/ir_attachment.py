# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import requests

from lxml import html
from odoo import models, api, fields
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import image_process
from dateutil.relativedelta import relativedelta
from datetime import datetime
from urllib.parse import urlparse


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def init(self):
        self._cr.execute("CREATE INDEX IF NOT EXISTS ir_attachment_link_preview_mimetype on ir_attachment(mimetype, write_date) WHERE mimetype IN ('image/o-linkpreview-image', 'application/o-linkpreview-with-thumbnail', 'application/o-linkpreview')")

    def _post_add_create(self):
        """ Overrides behaviour when the attachment is created through the controller
        """
        super(IrAttachment, self)._post_add_create()
        for record in self:
            record.register_as_main_attachment(force=False)

    def register_as_main_attachment(self, force=True):
        """ Registers this attachment as the main one of the model it is
        attached to.
        """
        self.ensure_one()
        if not self.res_model:
            return
        related_record = self.env[self.res_model].browse(self.res_id)
        if not related_record.check_access_rights('write', raise_exception=False):
            return
        # message_main_attachment_id field can be empty, that's why we compare to False;
        # we are just checking that it exists on the model before writing it
        if related_record and hasattr(related_record, 'message_main_attachment_id'):
            if force or not related_record.message_main_attachment_id:
                #Ignore AccessError, if you don't have access to modify the document
                #Just don't set the value
                try:
                    related_record.message_main_attachment_id = self
                except AccessError:
                    pass

    def _delete_and_notify(self):
        for attachment in self:
            if attachment.res_model == 'mail.channel' and attachment.res_id:
                target = self.env['mail.channel'].browse(attachment.res_id)
            else:
                target = self.env.user.partner_id
            self.env['bus.bus']._sendone(target, 'ir.attachment/delete', {
                'id': attachment.id,
            })
        self.unlink()

    def _attachment_format(self, commands=False):
        safari = request and request.httprequest.user_agent and request.httprequest.user_agent.browser == 'safari'
        attachments = []
        for attachment in self:
            res = {
                'checksum': attachment.checksum,
                'description': attachment.description,
                'id': attachment.id,
                'filename': attachment.name,
                'name': attachment.name,
                'mimetype': 'application/octet-stream' if safari and attachment.mimetype and 'video' in attachment.mimetype else attachment.mimetype,
                'url': attachment.url,
            }
            if attachment.res_id and issubclass(self.pool[attachment.res_model], self.pool['mail.thread']):
                main_attachment = self.env[attachment.res_model].sudo().browse(attachment.res_id).message_main_attachment_id
                res['is_main'] = attachment == main_attachment

            res['isEmpty'] = False
            image_mimetype = ['application/o-linkpreview-with-thumbnail', 'image/o-linkpreview-image']
            if not attachment.store_fname and not attachment.db_datas and attachment.mimetype in image_mimetype:
                res['isEmpty'] = True

            if commands:
                res['originThread'] = [('insert', {
                    'id': attachment.res_id,
                    'model': attachment.res_model,
                })]
            else:
                res.update({
                    'res_id': attachment.res_id,
                    'res_model': attachment.res_model,
                })
            attachments.append(res)
        return attachments

    def _throttle_link_preview(self, url):
        domain = urlparse(url).netloc
        date_interval = fields.Datetime.to_string((datetime.now() - relativedelta(seconds=10)))
        call = self.env['ir.attachment'].search_count([
            ('url', 'like', '%' + domain + '%'),
            ('write_date', '>', date_interval),
        ])
        # Since we are starting at 0, this is max 100 call to the same domain
        return call > 99

    @api.model
    def _create_link_preview(self, url, channel_partner):
        if self._throttle_link_preview(url):
            return False
        link_preview_data = self._get_link_preview_from_url(url)
        if link_preview_data:
            link_preview_data['res_model'] = 'mail.compose.message'
            link_preview_data['res_id'] = 0

        if self.env.user.share:
            # Only generate the access token if absolutely necessary (= not for internal user).
            link_preview_data['access_token'] = channel_partner.env['ir.attachment']._generate_access_token()

        if link_preview_data:
            attachment = self.sudo().create(link_preview_data)
            attachment_formated = attachment._attachment_format(commands=True)[0]
            if link_preview_data.get('access_token'):
                attachment_formated['accessToken'] = link_preview_data['access_token']
            return attachment_formated
        return False

    @api.model
    def _get_link_preview_from_url(self, url):
        try:
            response = requests.get(url, timeout=3)
        except requests.exceptions.RequestException:
            return False

        if response.status_code != requests.codes.ok:
            return False

        image_mimetype = [
            'image/bmp',
            'image/gif',
            'image/jpeg',
            'image/png',
            'image/tiff',
            'image/x-icon',
        ]
        if response.headers['Content-Type'] in image_mimetype:
            return {
                'url': url,
                'name': url,
                'description': False,
                'raw': self.resize_image(response.content),
                'mimetype': 'image/o-linkpreview-image',
            }
        if 'text/html' in response.headers['Content-Type']:
            return self._get_link_preview_from_html(url, response.content)
        return False

    def resize_image(self, image):
        return image_process(
            image,
            size=(300, 300),
            verify_resolution=True
        )

    def _fetch_and_resize_image_from_url(self, image_url):
        response = False
        try:
            response = requests.get(image_url, timeout=3)
        except requests.exceptions.RequestException:
            return False
        if response and response.status_code != requests.codes.ok:
            return False
        return self.resize_image(response.content)

    def _get_link_preview_from_html(self, url, content):
        tree = html.fromstring(content)
        title = tree.xpath('//meta[@property="og:title"]/@content')
        if title:
            title = title[0]
            image_url = tree.xpath('//meta[@property="og:image"]/@content')
            image = False
            if image_url:
                image = self._fetch_and_resize_image_from_url(image_url[0])
            description = tree.xpath('//meta[@property="og:description"]/@content')
            if description:
                description = description[0]
            return {
                'url': url,
                'name': title or url,
                'raw': image or False,
                'description': description or False,
                'mimetype': 'application/o-linkpreview-with-thumbnail' if image else 'application/o-linkpreview',
            }
        return False

    def _update_link_preview(self, sudo):
        # for attachment with image that have a missing image
        link_preview_data = self.env['ir.attachment']._get_link_preview_from_url(self.url)
        if link_preview_data:
            self.sudo(sudo).update(link_preview_data)
            return self._attachment_format(commands=True)[0]
        return False

    @api.autovacuum
    def _gc_link_preview(self):
        mimetypes = [
            'application/o-linkpreview',
            'image/o-linkpreview-image',
            'application/o-linkpreview-with-thumbnail',
        ]
        date_to_delete = fields.Date.to_string((datetime.now() + relativedelta(days=-7)))
        domain = [
            ('mimetype', 'in', mimetypes),
            ('write_date', '<', date_to_delete),
        ]
        records = self.sudo().search(domain)
        for record in records:
            # Delete the data but save the mimetype. This allow us be able to
            # regenerate the link preview when the message is displayed again.
            record.sudo().write({'raw': False, 'mimetype': record.mimetype})
