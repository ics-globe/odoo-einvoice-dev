# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.tools import str2bool
import base64

import logging

_logger = logging.getLogger(__name__)

# this is needed because the account.edi.format codes do not necessarily match
# the suffix of the class used to generate the xml file (and it would be weird to
# rename account.edi.xml.cii into account.edi.xml.facturx_1_0_05 + we would need to change it
# everytime the code of the account.edi.format changes
# TODO: in master, get rid of this by removing old account.edi.formats and creating new ones, with names matching
#  the suffixes
# only the formats matching the keys of this dict will be generated (if enabled on journal)
FORMAT_CODE_TO_CLASS_SUFFIX = {
    'facturx_1_0_05': 'cii',
    'ubl_2_1': 'ubl_21',  # this is kept because the format already exists -> it's present on the journal
    # if this line is commented, even if it is checked in the journal, nothing is generated.
    'ubl_bis3': 'ubl_bis3',
    'ubl_de': 'ubl_de',
    'nlcius_1': 'ubl_nl',
    'ehf_3': 'ubl_no',
}

class AccountEdiFormat(models.Model):
    _name = 'account.edi.format'
    _inherit = 'account.edi.format'

    ####################################################
    # Helpers
    ####################################################

    def _infer_xml_builder_from_tree(self, tree):
        self.ensure_one()
        ubl_version = tree.find('{*}UBLVersionID')
        customization_id = tree.find('{*}CustomizationID')
        if tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice':
            return self.env['account.edi.xml.cii']
        if customization_id is not None:
            if 'xrechnung' in customization_id.text:
                return self.env['account.edi.xml.ubl_de']
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0':
                return self.env['account.edi.xml.ubl_bis3']
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0':
                return self.env['account.edi.xml.ubl_nl']
        if ubl_version is not None:
            if ubl_version.text == '2.0':
                return self.env['account.edi.xml.ubl_20']
            if ubl_version.text == '2.1':
                return self.env['account.edi.xml.ubl_21']
        return

    def _is_generation_possible(self, company):
        """
        Returns a boolean indicating whether it is possible to generate an xml file using one of the formats from this
        module or not
        """
        format_class_suffix = FORMAT_CODE_TO_CLASS_SUFFIX.get(self.code)
        return format_class_suffix and self.env['account.edi.xml.' + format_class_suffix]._get_xml_builder(self.code, company)

    ####################################################
    # Export: Account.edi.format override
    ####################################################

    def _is_required_for_invoice(self, invoice):
        # OVERRIDE
        self.ensure_one()

        if not self._is_generation_possible(invoice.company_id):
            return super()._is_required_for_invoice(invoice)

        if invoice.move_type not in ('out_invoice', 'out_refund'):
            return False
        return True

    def _is_enabled_by_default_on_journal(self, journal):
        # OVERRIDE
        self.ensure_one()

        # only treat the format created in this module, for the others (like facturx_1_0_05, nlcius_1, ehf_3),
        # keep the behaviour unchanged
        if self.code in ['ubl_de', 'ubl_bis3']:
            return False

        return super()._is_enabled_by_default_on_journal(journal)

    def _post_invoice_edi(self, invoices, test_mode=False):
        # OVERRIDE
        self.ensure_one()

        if self.code not in FORMAT_CODE_TO_CLASS_SUFFIX:
            return super()._post_invoice_edi(invoices)

        # if the builder is empty (for instance, Bis 3 cannot be generated if the company is not in EAS)
        if not self._is_generation_possible(invoices[0].company_id):
            for invoice in invoices:
                # we don't want the edi_document to appear on the account_move, tab "EDI documents" with state
                # 'To Send' forever (because it will never be generated), otherwise, we cannot uncheck the edi_format
                # on the journal ("because some documents are not synchronised", since they are not send)
                invoice.edi_document_ids.filtered(lambda doc: doc.edi_format_id == self).state = 'cancelled'
            return super()._post_invoice_edi(invoices)

        res = {}
        for invoice in invoices:
            format_class_suffix = FORMAT_CODE_TO_CLASS_SUFFIX.get(self.code)
            res = self.env['account.edi.xml.' + format_class_suffix]._get_xml_builder(self.code, invoice.company_id)

            xml_content, errors = res['export_invoice'](invoice)

            # DEBUG: send directly to the test platform (the one used by ecosio)
            #response = self.env['account.edi.common']._check_xml_ecosio(invoice, xml_content, res['ecosio_format'])
            #print("Response: ", response['Result'])

            attachment_create_vals = {
                'name': res['invoice_filename'](invoice),
                'datas': base64.encodebytes(xml_content.encode('utf-8')),
                'mimetype': 'application/xml'
            }
            # we don't want the facturx xml to appear in the attachment of the invoice when confirming it
            if self.code != 'facturx_1_0_05':
                attachment_create_vals.update({'res_id': invoice.id, 'res_model': 'account.move'})

            attachment = self.env['ir.attachment'].create(attachment_create_vals)
            res[invoice] = {
                'success': True,
                'attachment': attachment,
            }
            # It's annoying because if there are errors, you cannot uncheck the edi_format on the journal
            # because the corresponding edi_document on the account_move is marked as "To Send" (in red)
            # If no errors occur, it's marked as "Sent" and you can uncheck the edi_format.
            if errors:
                res[invoice].update({
                    'success': True,  #TODO: if no modif in _postprocess_post_edi_results, this should be False, otherwise the 'error' is not parsed
                    'error': _("Errors occured while creating the EDI document (format: %s). The receiver "
                               "might refuse it.", self.env['account.edi.xml.' + format_class_suffix]._description)
                             + '<p> <li>' + "</li> <li>".join(errors) + '</li> </p>',
                    'blocking_level': 'info',
                })

        return res

    def _is_embedding_to_invoice_pdf_needed(self):
        # OVERRIDE
        self.ensure_one()

        if self.code == 'facturx_1_0_05':
            return True
        return super()._is_embedding_to_invoice_pdf_needed()

    def _prepare_invoice_report(self, pdf_writer, edi_document):
        self.ensure_one()
        if self.code != 'facturx_1_0_05':
            return super()._prepare_invoice_report(pdf_writer, edi_document)
        if not edi_document.attachment_id:
            return

        pdf_writer.embed_odoo_attachment(edi_document.attachment_id, subtype='text/xml')
        if not pdf_writer.is_pdfa and str2bool(
                self.env['ir.config_parameter'].sudo().get_param('edi.use_pdfa', 'False')):
            try:
                pdf_writer.convert_to_pdfa()
            except Exception as e:
                _logger.exception("Error while converting to PDF/A: %s", e)
            metadata_template = self.env.ref('account_edi_facturx.account_invoice_pdfa_3_facturx_metadata',
                                             raise_if_not_found=False)
            if metadata_template:
                pdf_writer.add_file_metadata(metadata_template._render({
                    'title': edi_document.move_id.name,
                    'date': fields.Date.context_today(self),
                }).encode())

    ####################################################
    # Import: Account.edi.format override
    ####################################################

    def _create_invoice_from_xml_tree(self, filename, tree, journal=None):
        # OVERRIDE
        self.ensure_one()

        if not journal:
            # infer the journal
            journal = self.env['account.journal'].search([
                ('company_id', '=', self.env.company.id), ('type', '=', 'purchase')
            ], limit=1)

        if not self._is_generation_possible(journal.company_id):
            return super()._create_invoice_from_xml_tree(filename, tree, journal=journal)

        # infer the xml builder
        invoice_xml_builder = self._infer_xml_builder_from_tree(tree)

        if invoice_xml_builder is not None:
            invoice = invoice_xml_builder._import_invoice(journal, filename, tree)
            if invoice:
                return invoice

        return super()._create_invoice_from_xml_tree(filename, tree, journal=journal)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        # OVERRIDE
        self.ensure_one()

        if not self._is_generation_possible(invoice.company_id):
            return super()._update_invoice_from_xml_tree(filename, tree, invoice)

        # infer the xml builder
        invoice_xml_builder = self._infer_xml_builder_from_tree(tree)

        if invoice_xml_builder is not None:
            invoice = invoice_xml_builder._import_invoice(invoice.journal_id, filename, tree, invoice)
            if invoice:
                return invoice

        return super()._update_invoice_from_xml_tree(filename, tree, invoice)
