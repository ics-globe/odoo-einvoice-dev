# -*- coding: utf-8 -*-
from odoo.addons.account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.tests import tagged
import base64

@tagged('post_install', '-at_install')
class TestUBLBE(TestUBLCommon):

    @classmethod
    def setUpClass(cls,
                   chart_template_ref="l10n_be.l10nbe_chart_template",
                   #chart_template_ref=None,
                   edi_format_ref="account_edi_ubl_cii.ubl_bis3",
                   ):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        # seller
        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Chaussée de Namur 40",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0202239951',
            'country_id': cls.env.ref('base.be').id,
            'bank_ids': [(0, 0, {'acc_number': 'BE15001559627230'})],
        })

        # buyer
        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Rue des Bourlottes 9",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0477472701',
            'country_id': cls.env.ref('base.be').id,
            'bank_ids': [(0, 0, {'acc_number': 'BE90735788866632'})],
        })

        cls.tax_25 = cls.env['account.tax'].create({
            'name': 'tax_25',
            'amount_type': 'percent',
            'amount': 25,
            'type_tax_use': 'sale',
            # 'country_id': cls.env.ref('base.be').id,
        })

        cls.tax_21 = cls.env['account.tax'].create({
            'name': 'tax_21',
            'amount_type': 'percent',
            'amount': 21,
            'type_tax_use': 'sale',
            #'country_id': cls.env.ref('base.be').id,
        })

        cls.tax_15 = cls.env['account.tax'].create({
            'name': 'tax_15',
            'amount_type': 'percent',
            'amount': 15,
            'type_tax_use': 'sale',
            # 'country_id': cls.env.ref('base.be').id,
        })

        cls.tax_12 = cls.env['account.tax'].create({
            'name': 'tax_12',
            'amount_type': 'percent',
            'amount': 12,
            'type_tax_use': 'sale',
            #'country_id': cls.env.ref('base.be').id,
        })

        cls.tax_0 = cls.env['account.tax'].create({
            'name': 'tax_0',
            'amount_type': 'percent',
            'amount': 0,
            'type_tax_use': 'sale',
            # 'country_id': cls.env.ref('base.be').id,
        })

        cls.acc_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'BE15001559627231',
            'partner_id': cls.company_data['company'].partner_id.id,
        })

        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': cls.journal.id,
            'partner_id': cls.partner_1.id,
            'partner_bank_id': cls.acc_bank,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'product_uom_id': cls.env.ref('uom.product_uom_dozen').id,
                'price_unit': 275.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, cls.tax_21.ids)],
            })],
        })

    @classmethod
    def setup_company_data(cls, company_name, chart_template):
        # OVERRIDE
        # to force the company to be belgian
        res = super().setup_company_data(
            company_name,
            chart_template=chart_template,
            country_id=cls.env.ref("base.be").id,
            vat="BE0246697724")
        return res

    ####################################################
    # Test export - import
    ####################################################

    def test_export_xml(self):
        # post the invoice created in the setupclass -> only generate the xml from the edi_format_ref param
        self.invoice.action_post()
        self.assertEqual(self.invoice.attachment_ids.mapped("name"), ['INV_2017_01_0001_ubl_bis3.xml'])

        # create a new invoice -> generates all the xmls (if multiple), as if we created an invoice in the UI.
        invoice = self._generate_invoice(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                    'price_unit': 990.0,
                    'tax_ids': [(6, 0, self.tax_21.ids)],
                },
            ],
        )
        invoice.action_post()
        self.assertEqual(
            set(invoice.attachment_ids.mapped("name")),
            {
                'INV_2017_01_0002_ubl_21.xml',
                'INV_2017_01_0002_ubl_20.xml',
                'factur-x.xml',
                'INV_2017_01_0002_ubl_bis3.xml',
            }
        )

    def test_export_import_invoice(self):
        invoice, xml_etree, xml_filename = self._export_invoice(
            self.partner_1,
            self.partner_2,
            xpaths='''
                <xpath expr=".//*[local-name()='InvoiceLine'][1]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='InvoiceLine'][2]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='InvoiceLine'][3]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='PaymentMeans']/*[local-name()='PaymentID']" position="replace">
                    <PaymentID>___ignore___</PaymentID>
                </xpath>
            ''',
            expected_file='test_be_out_invoice.xml',
            export_file='export_out_invoice.xml',
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                    'price_unit': 990.0,
                    'discount': 10.0,
                    'tax_ids': [(6, 0, self.tax_21.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_12.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': -1.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_12.ids)],
                },
            ],
        )
        self.assertEqual(xml_filename[-12:], "ubl_bis3.xml")  # ensure we test the right format !
        self._import_invoice(invoice, xml_etree, xml_filename)

    def test_export_import_refund(self):
        invoice, xml_etree, xml_filename = self._export_invoice(
            self.partner_1,
            self.partner_2,
            xpaths='''
                <xpath expr=".//*[local-name()='CreditNoteLine'][1]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='CreditNoteLine'][2]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='CreditNoteLine'][3]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
            ''',
            expected_file='test_be_out_refund.xml',
            export_file='export_out_refund.xml',
            move_type='out_refund',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                    'price_unit': 990.0,
                    'discount': 10.0,
                    'tax_ids': [(6, 0, self.tax_21.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_12.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': -1.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_12.ids)],
                },
            ],
        )
        self.assertEqual(xml_filename[-12:], "ubl_bis3.xml")
        self._import_invoice(invoice, xml_etree, xml_filename)

    ####################################################
    # Test import
    ####################################################

    def test_import_invoice_xml(self):
        invoice = self._create_empty_vendor_bill()
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('account_edi_ubl_cii_tests', 'test_files', 'test_be_out_invoice.xml', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 3164.22)  # see cbc:PayableAmount

        self.create_invoice_from_file('account_edi_ubl_cii_tests', 'test_files', 'test_be_out_invoice.xml')

        self.assertEqual(invoice.amount_total, 3164.22)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)

    def test_import_export_invoice_xml(self):
        """
        Test whether the elements only specific to ubl_be are correctly exported
        and imported in the xml file
        """
        self.invoice.action_post()
        attachment = self.invoice._get_edi_attachment(self.edi_format)
        self.assertTrue(attachment)
        xml_content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        xml_etree = self.get_xml_tree_from_string(xml_content)

        self.assertEqual(
            xml_etree.find('{*}ProfileID').text,
            'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0'
        )
        self.assertEqual(
            xml_etree.find('{*}CustomizationID').text,
            'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0'
        )
        # Export: in bis3, under Country, the Name element should not appear, but IdentificationCode still should
        self.assertIsNotNone(xml_etree.find('.//{*}Country/{*}IdentificationCode'))
        self.assertIsNone(xml_etree.find('.//{*}Country/{*}Name'))

        # Import:
        journal_id = self.company_data['default_journal_sale']
        action_vals = journal_id.with_context(default_move_type='in_invoice').create_invoice_from_attachment(
            attachment.ids)
        created_bill = self.env['account.move'].browse(action_vals['res_id'])
        self.assertTrue(created_bill)

    ####################################################
    # Test import: Bis 3 examples from OpenPEPPOL
    # xmls come from https://github.com/OpenPEPPOL/peppol-bis-invoice-3/tree/master/rules/examples
    ####################################################

    def test_open_peppol_xml_import(self):
        subfolder = 'test_files/peppol-bis-invoice-3'
        self._import_invoice_from_file(subfolder=subfolder, filename='Allowance-example.xml', amount_total=6125,
                                       amount_tax=1225)
        self._import_invoice_from_file(subfolder=subfolder, filename='base-creditnote-correction.xml',
                                       amount_total=1656.25, amount_tax=331.25, move_type='in_refund')
        self._import_invoice_from_file(subfolder=subfolder, filename='base-example.xml',
                                       amount_total=1656.25, amount_tax=331.25)
        self._import_invoice_from_file(subfolder=subfolder, filename='base-negative-inv-correction.xml',
                                       amount_total=1656.25, amount_tax=331.25, move_type='in_refund')
        self._import_invoice_from_file(subfolder=subfolder, filename='vat-category-E.xml',
                                       amount_total=1200, amount_tax=0, currency='GBP')
        self._import_invoice_from_file(subfolder=subfolder, filename='vat-category-O.xml',
                                       amount_total=3200, amount_tax=0, currency='SEK')
        self._import_invoice_from_file(subfolder=subfolder, filename='vat-category-S.xml',
                                       amount_total=8550, amount_tax=1550)
        self._import_invoice_from_file(subfolder=subfolder, filename='vat-category-Z.xml',
                                       amount_total=1200, amount_tax=0, currency='GBP')
