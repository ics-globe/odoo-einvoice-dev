# -*- coding: utf-8 -*-
from odoo.addons.account_edi_peppol_tests.tests.common import TestUBLCommon
from odoo.tests import tagged
import base64


@tagged('post_install', '-at_install')
class TestUBLDE(TestUBLCommon):

    @classmethod
    def setUpClass(cls,
                   #chart_template_ref="l10n_de_skr03.l10n_de_chart_template",
                   chart_template_ref=None,
                   ):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Legoland-Allee 3",
            'zip': "89312",
            'city': "Günzburg",
            'vat': 'DE257486969',
            'phone': '+49 180 6 225789',
            'email': 'info@legoland.de',
            'country_id': cls.env.ref('base.de').id,
            'bank_ids': [(0, 0, {'acc_number': 'DE48500105176424548921'})],
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Europa-Park-Straße 2",
            'zip': "77977",
            'city': "Rust",
            'vat': 'DE186775212',
            'country_id': cls.env.ref('base.de').id,
            'bank_ids': [(0, 0, {'acc_number': 'DE50500105175653254743'})],
        })

        cls.tax_19 = cls.env['account.tax'].create({
            'name': 'tax_19',
            'amount_type': 'percent',
            'amount': 19,
            'type_tax_use': 'sale',
            #'country_id': cls.env.ref('base.de').id,
        })

        cls.tax_7 = cls.env['account.tax'].create({
            'name': 'tax_7',
            'amount_type': 'percent',
            'amount': 7,
            'type_tax_use': 'sale',
            #'country_id': cls.env.ref('base.de').id,
        })

        cls.acc_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'BE15001559627232',
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
                'tax_ids': [(6, 0, cls.tax_19.ids)],
            })],
        })

    @classmethod
    def setup_company_data(cls, company_name, chart_template):
        # OVERRIDE
        # to force the company to be german + add phone and email
        res = super().setup_company_data(
            company_name,
            chart_template=chart_template,
            country_id=cls.env.ref("base.de").id,
            phone="+49(0) 30 227-0",
            email="test@xrechnung@com"
        )
        return res

    ####################################################
    # Test export
    ####################################################

    def test_out_invoice(self):
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
            ''',
            expected_file='test_de_out_invoice.xml',
            export_file='export_out_invoice.xml',
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'quantity': 10.0,
                    'price_unit': 990.0,
                    'discount': 10.0,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                },
                {
                    'quantity': 10.0,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_7.ids)],
                },
                {
                    'quantity': -1.0,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_7.ids)],
                },
            ],
        )

        self._import_invoice(invoice, xml_etree, xml_filename)

    def test_out_refund(self):
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
            expected_file='test_de_out_refund.xml',
            export_file='export_out_refund_bis3.xml',
            move_type='out_refund',
            invoice_line_ids=[
                {
                    'quantity': 10.0,
                    'price_unit': 990.0,
                    'discount': 10.0,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                },
                {
                    'quantity': 10.0,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_7.ids)],
                },
                {
                    'quantity': -1.0,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_7.ids)],
                },
            ],
        )

        self._import_invoice(invoice, xml_etree, xml_filename)

    def test_export_pdf(self):
        self.invoice.action_post()
        pdf_values = self.edi_format._get_embedding_to_invoice_pdf_values(self.invoice)
        self.assertEqual(pdf_values['name'], 'peppol.xml')

    ####################################################
    # Test import
    ####################################################

    def test_invoice_edi_pdf(self):
        invoice = self._create_empty_vendor_bill()
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('account_edi_peppol_tests', 'test_files', 'test_de_in_invoice.pdf', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 4195.86)

        self.create_invoice_from_file('account_edi_peppol_tests', 'test_files', 'test_de_in_invoice.pdf')

        self.assertEqual(invoice.amount_total, 4195.86)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)

    def test_invoice_edi_xml(self):
        invoice = self._create_empty_vendor_bill()
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('account_edi_peppol_tests', 'test_files', 'test_de_out_invoice.xml', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 11565.9)  # see cbc:PayableAmount

        self.create_invoice_from_file('account_edi_peppol_tests', 'test_files', 'test_de_out_invoice.xml')

        self.assertEqual(invoice.amount_total, 11565.9)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)

    def test_invoice_export_import_xml(self):
        """
        Test whether the elements which are only specific to ubl_de are correctly exported
        and imported in the xml file
        """
        partner = self.invoice.commercial_partner_id
        self.invoice.action_post()
        attachment = self.invoice._get_edi_attachment(self.edi_format)
        self.assertTrue(attachment)
        xml_content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        xml_etree = self.get_xml_tree_from_string(xml_content)

        # Export: BuyerReference is in the out_invoice xml
        self.assertEqual(xml_etree.find('{*}BuyerReference').text, partner.name)
        self.assertEqual(
            xml_etree.find('{*}CustomizationID').text,
            'urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_2.2#conformant#urn:xoev-de:kosit:extension:xrechnung_2.2'
        )

        journal_id = self.company_data['default_journal_sale']
        action_vals = journal_id.with_context(default_move_type='in_invoice').create_invoice_from_attachment(
            attachment.ids)
        created_bill = self.env['account.move'].browse(action_vals['res_id'])
        self.assertTrue(created_bill)
