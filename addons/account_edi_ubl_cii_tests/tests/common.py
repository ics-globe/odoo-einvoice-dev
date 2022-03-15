# -*- coding: utf-8 -*-
import base64

from freezegun import freeze_time

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo import fields
from odoo.modules.module import get_resource_path

class TestUBLCommon(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None, edi_format_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        # Ensure the testing currency is using a valid ISO code.
        real_usd = cls.env.ref('base.USD')
        real_usd.name = 'FUSD'
        real_usd.flush(['name'])
        cls.currency_data['currency'].name = 'USD'

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        # OVERRIDE to force the company with EUR currency.
        eur = cls.env.ref('base.EUR')
        if not eur.active:
            eur.active = True

        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].currency_id = eur
        return res

    @classmethod
    def _get_tax_by_xml_id(cls, tax_xml_id):
        """ Helper to retrieve a tax easily.

        :param tax_xml_id:  The tax template's xml id.
        :return:            An account.tax record
        """
        module, trailing_id = tax_xml_id.split('.')
        return cls.env.ref(f'{module}.{cls.env.company.id}_{trailing_id}')

    def assert_same_invoice(self, invoice1, invoice2, **invoice_kwargs):
        self.assertEqual(len(invoice1.invoice_line_ids), len(invoice2.invoice_line_ids))
        self.assertRecordValues(invoice2, [{
            'partner_id': invoice1.company_id.partner_id.id,
            'invoice_date': fields.Date.from_string(invoice1.date),
            'currency_id': invoice1.currency_id.id,
            'amount_untaxed': invoice1.amount_untaxed,
            'amount_tax': invoice1.amount_tax,
            'amount_total': invoice1.amount_total,
            **invoice_kwargs,
        }])

        default_invoice_line_kwargs_list = [{}] * len(invoice1.invoice_line_ids)
        invoice_line_kwargs_list = invoice_kwargs.get('invoice_line_ids', default_invoice_line_kwargs_list)
        self.assertRecordValues(invoice2.invoice_line_ids, [{
            'quantity': line.quantity,
            'price_unit': line.price_unit,
            'discount': line.discount,
            'product_id': line.product_id.id,
            'tax_ids': line.tax_ids.ids,
            'product_uom_id': line.product_uom_id.id,
            **invoice_line_kwargs,
        } for line, invoice_line_kwargs in zip(invoice1.invoice_line_ids, invoice_line_kwargs_list)])

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    @freeze_time('2017-01-01')
    def _import_invoice(self, invoice, xml_etree, xml_filename):
        new_invoice = self.edi_format._create_invoice_from_xml_tree(
            xml_filename,
            xml_etree,
            self.company_data['default_journal_purchase'],
        )

        self.assertTrue(new_invoice)
        self.assert_same_invoice(invoice, new_invoice)

    def _import_invoice_from_file(self, subfolder, filename, amount_total, amount_tax, move_type='in_invoice', currency='EUR'):
        # import the file as a new invoice / update the invoice from file
        # assert that the amount_total, amount_tax, currency is correct
        invoice = self._create_empty_vendor_bill()
        invoice.move_type = move_type
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('account_edi_ubl_cii_tests', subfolder, filename, invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)

        self.assertEqual(invoice.amount_total, amount_total)
        self.assertEqual(invoice.amount_tax, amount_tax)
        self.assertEqual(invoice.currency_id.name, currency)

        self.create_invoice_from_file('account_edi_ubl_cii_tests', subfolder, filename)

        self.assertEqual(invoice.amount_total, amount_total)
        self.assertEqual(invoice.amount_tax, amount_tax)
        self.assertEqual(invoice.currency_id.name, currency)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    @freeze_time('2017-01-01')
    def _generate_invoice(self, seller, buyer, **invoice_kwargs):
        # Setup the seller.
        self.env.company.write({
            'partner_id': seller.id,
            'name': seller.name,
            'street': seller.street,
            'zip': seller.zip,
            'city': seller.city,
            'vat': seller.vat,
            'country_id': seller.country_id.id,
        })

        move_type = invoice_kwargs['move_type']
        invoice = self.env['account.move'].create({
            'partner_id': buyer.id,
            'partner_bank_id': (seller if move_type == 'out_invoice' else buyer).bank_ids[:1].id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_origin': 'test invoice origin',
            'narration': 'test narration',
            **invoice_kwargs,
            'invoice_line_ids': [
                (0, 0, {
                    'sequence': i,
                    **invoice_line_kwargs,
                })
                for i, invoice_line_kwargs in enumerate(invoice_kwargs.get('invoice_line_ids', []))
            ],
        })
        return invoice

    def _export_invoice(self, seller, buyer, xpaths='', expected_file='', export_file=False, **invoice_kwargs):
        invoice = self._generate_invoice(seller, buyer, **invoice_kwargs)
        invoice.action_post()

        attachment = invoice._get_edi_attachment(self.edi_format)
        self.assertTrue(attachment)
        xml_filename = attachment.name
        xml_content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        xml_etree = self.get_xml_tree_from_string(xml_content)

        # DEBUG: uncomment to get the generated xml and then, be able to submit it online for validation.
        #if export_file:
        #    with open(export_file, 'wb+') as f:
        #        f.write(xml_content)

        expected_file_path = get_resource_path('account_edi_ubl_cii_tests', 'test_files', expected_file)
        expected_etree = self.get_xml_tree_from_string(open(expected_file_path, "r").read())

        modified_etree = self.with_applied_xpath(
            expected_etree,
            xpaths
        )

        # DEBUG: uncomment to get the generated xml to which the xpath modifications have been applied
        #from lxml import etree
        #et = etree.ElementTree(modified_etree)
        #et.write('modified_etree.xml', pretty_print=True)

        self.assertXmlTreeEqual(
            xml_etree,
            modified_etree,
        )

        return invoice, xml_etree, xml_filename
