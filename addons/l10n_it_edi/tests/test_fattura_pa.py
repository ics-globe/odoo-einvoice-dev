# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from unittest.mock import patch
import freezegun
from lxml import etree

from odoo import tools
from odoo.tests import tagged
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class ProxyUserTests(AccountEdiTestCommon):
    """ Main test class for the l10n_it_edi vendor bills XML import from the proxy user"""

    fake_test_content = """<?xml version="1.0" encoding="UTF-8"?>
        <p:FatturaElettronica versione="FPR12" xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
        xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2 http://www.fatturapa.gov.it/export/fatturazione/sdi/fatturapa/v1.2/Schema_del_file_xml_FatturaPA_versione_1.2.xsd">
          <FatturaElettronicaHeader>
            <CessionarioCommittente>
              <DatiAnagrafici>
                <CodiceFiscale>01234560157</CodiceFiscale>
              </DatiAnagrafici>
            </CessionarioCommittente>
          </FatturaElettronicaHeader>
          <FatturaElettronicaBody>
            <DatiGenerali>
              <DatiGeneraliDocumento>
                <TipoDocumento>TD02</TipoDocumento>
              </DatiGeneraliDocumento>
            </DatiGenerali>
          </FatturaElettronicaBody>
        </p:FatturaElettronica>"""

    @classmethod
    def setUpClass(cls):
        """ Setup the test class with a proxy user and a fake fatturaPA content """

        super().setUpClass(chart_template_ref='l10n_it.l10n_it_chart_template_generic',
                           edi_format_ref='l10n_it_edi.edi_fatturaPA')

        # Use the company_data_2 to test that the e-invoice is imported for the right company
        cls.company = cls.company_data_2['company']

        # Initialize the company's codice fiscale
        cls.company.vat = "IT01234560157"
        cls.company.l10n_it_codice_fiscale = cls.company.vat

        # Build test data.
        # invoice_filename1 is used for vendor bill receipts tests
        # invoice_filename2 is used for vendor bill tests
        cls.invoice_filename1 = 'IT01234567890_FPR01.xml'
        cls.invoice_filename2 = 'IT01234567890_FPR02.xml'
        cls.signed_invoice_filename = 'IT01234567890_FPR01.xml.p7m'
        cls.invoice_content = cls._get_test_file_content(cls.invoice_filename1)
        cls.signed_invoice_content = cls._get_test_file_content(cls.signed_invoice_filename)
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'ref': '01234567890'
        })
        cls.attachment = cls.env['ir.attachment'].create({
            'name': cls.invoice_filename1,
            'raw': cls.invoice_content,
            'res_id': cls.invoice.id,
            'res_model': 'account.move',
        })
        cls.edi_document = cls.env['account.edi.document'].create({
            'edi_format_id': cls.edi_format.id,
            'move_id': cls.invoice.id,
            'attachment_id': cls.attachment.id,
            'state': 'sent'
        })

        cls.proxy_user = cls.env['account_edi_proxy_client.user'].sudo().create({
            'id_client': 'TEST_PROXY_ID_CLIENT_1234',
            'edi_format_id': cls.edi_format.id,
            'edi_identification': 'IT01234560157',
            'private_key': b'\x00',
        })

        cls.partner_a.vat = "IT07643520567"
        cls.partner_a.l10n_it_codice_fiscale = cls.partner_a.vat
        cls.customer_bank = cls.env['res.partner.bank'].with_company(cls.company).create({
            'acc_number': '0123456789',
            'bank_id': cls.env.ref('base.bank_bnp').id,
            'partner_id': cls.partner_a.id,
        })

        cls.invoice_to_post = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'partner_bank_id': cls.customer_bank.id,
            'payment_reference': 'test payment reference',
            'invoice_line_ids': [
                (0, 0, {
                    'name': cls.product_a.name,
                    'product_id': cls.product_a.id,
                    'account_id': cls.company_data_2['default_account_receivable'],
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                    'currency_id': cls.company_data['currency'].id,
                })
            ]
        })

    @classmethod
    def _get_test_file_content(cls, filename):
        """ Get the content of a test file inside this module """
        path = 'l10n_it_edi/tests/expected_xmls/' + filename
        with tools.file_open(path, mode='rb') as test_file:
            return test_file.read()

    def _create_invoice(self, content, filename):
        """ Create an invoice from given attachment content """
        if filename.endswith(".p7m"):
            content = remove_signature(content)
        tree = etree.fromstring(content)
        return self.edi_format.sudo()._create_invoice_from_xml_tree(filename, tree)

    def _fake_cron_reception(self, fake_results):
        """ Run the cron function that checks the proxy for invoices and creates them,
            but provide the expected invoices.

            :param fake_results:
                Dictionary of the form {id_transaction: fattura, ...} matching the results
                that would be returned by the _make_request function to the proxy

        """

        with patch('odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user.AccountEdiProxyClientUser._make_request', return_value=fake_results), \
            patch('odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user.AccountEdiProxyClientUser._decrypt_data', new=lambda _self, x, key: remove_signature(x) if key else x), \
            patch('odoo.addons.base.models.ir_config_parameter.IrConfigParameter.get_param', new=lambda *args: None if len(args) == 2 else args[-1]):

            self.edi_format._cron_receive_fattura_pa()

    # -----------------------------
    #
    # Receive Vendor bills
    #
    # -----------------------------

    def test_recieve_vendor_bill(self):
        """ Test a sample e-invoice file from https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.2/IT01234567890_FPR01.xml """

        fattura = {
            'filename': self.invoice_filename1,
            'file': self.invoice_content,
            'key': False,
        }

        self._fake_cron_reception({'00000001': fattura})
        attachment = self.env['ir.attachment'].search([('name', '=', fattura['filename'])])
        self.assertEqual(len(attachment), 1)
        invoice = self.env['account.move'].browse(attachment.res_id)

        self.assertTrue(bool(invoice))


    def test_receive_signed_vendor_bill(self):
        """ Test a signed (P7M) sample e-invoice file from https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.2/IT01234567890_FPR01.xml """
        with freezegun.freeze_time('2020-04-06'):

            signed_fattura = {
                'filename': self.signed_invoice_filename,
                'file': self.signed_invoice_content,
                'key': 'FAKE_KEY'
            }

            self._fake_cron_reception({'00000002': signed_fattura})
            attachment = self.env['ir.attachment'].search([('name', '=', signed_fattura['filename'])])
            self.assertEqual(len(attachment), 1)
            invoice = self.env['account.move'].browse(attachment.res_id)

            self.assertTrue(bool(invoice))

    @patch('logging.Logger.info')
    def test_receive_same_vendor_bill_twice(self, log):
        """ Test that the second time we receive a bill, the second is discarded """
        content = self.fake_test_content.encode()
        fattura = {
            'filename': self.invoice_filename2,
            'file': content,
            'key': False
        }

        self._fake_cron_reception({'00000003': fattura})
        self._fake_cron_reception({'00000003': fattura})
        log.assert_called_with('E-invoice already exist: %s', self.invoice_filename2)

    # -----------------------------
    #
    # Post invoices
    #
    # -----------------------------

    def _test_post_step_1(self, invoices):

        fake_upload_results = {self.edi_format._l10n_it_edi_generate_electronic_invoice_filename(invoice): {
            'id_transaction': f"test_id_transaction_{invoice.id}",
            'invoice': invoice
        } for invoice in invoices}

        with patch('odoo.addons.account_edi_proxy_client.models.account_edi_format.AccountEdiFormat._get_proxy_user', return_value=self.proxy_user), \
             patch('odoo.addons.l10n_it_edi.models.account_edi_format.AccountEdiFormat._l10n_it_edi_upload', return_value=fake_upload_results), \
             patch('odoo.addons.base.models.ir_config_parameter.IrConfigParameter.get_param', new=lambda *args, **kwargs: None if len(args) == 2 else kwargs.get('default') or args[-1]):
            message = self.edi_format._l10n_it_post_invoices_step_1(invoices)
            expected_message = {
                invoice: {
                    'id_transaction': f"test_id_transaction_{invoice.id}",
                    'invoice': invoice,
                    'error': 'The invoice was successfully transmitted to the Public Administration and we are waiting for confirmation.',
                    'blocking_level': 'info'
                }
                for invoice in invoices
            }
            self.assertEqual(message, expected_message)

            return message

    def _test_post_step_2(self, invoice, fake_results):

        with patch('odoo.addons.account_edi_proxy_client.models.account_edi_format.AccountEdiFormat._get_proxy_user', return_value=self.proxy_user), \
             patch('odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user.AccountEdiProxyClientUser._make_request', return_value=fake_results), \
             patch('odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user.AccountEdiProxyClientUser._decrypt_data', new=lambda _self, x, key: remove_signature(x) if key else x), \
             patch('odoo.addons.base.models.ir_config_parameter.IrConfigParameter.get_param', new=lambda *args: None if len(args) == 2 else args[-1]):
            message = self.edi_format._l10n_it_post_invoices_step_2(invoice)
            return message

    @patch('logging.Logger.info')
    def test_post_fattura_pa(self, log):

        invoice = self.invoice_to_post
        message = self._test_post_step_1(invoice)

        tree = etree.fromstring(invoice.l10n_it_edi_attachment_id.raw)

        outcome = etree.Element('Esito')
        outcome.text = 'EC01'
        tree.append(outcome)

        fake_results = {content['id_transaction']: {
            'filename': invoice.l10n_it_edi_attachment_id.name,
            'file': etree.tostring(tree),
            'key': False,
            'state': 'notificaEsito',
        } for invoice, content in message.items()}

        message = self._test_post_step_2(invoice, fake_results)
        self.assertEqual(message[invoice], {
            'attachment': invoice.l10n_it_edi_attachment_id,
            'success': True,
        })
