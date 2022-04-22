# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models, tools

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _search_attachment_and_validate_xml(self, xml_content, xsd_name, reload_files_function=None):
        """Try and validate the XML content with an XSD attachment.
        If the XSD attachment cannot be found in database, (re)load it.

        :param xml_content: the XML content to validate
        :param xsd_name: the XSD file name in database
        :return: the result of the function :func:`odoo.tools.xml_utils._check_with_xsd`
        """
        try:
            tools.xml_utils._check_with_xsd(xml_content, xsd_name, self.env)
        except FileNotFoundError:
            if not reload_files_function:
                _logger.warning("You need to provide a function used to (re)load XSD files")
            reload_files_function()
            tools.xml_utils._check_with_xsd(xml_content, xsd_name, self.env)
