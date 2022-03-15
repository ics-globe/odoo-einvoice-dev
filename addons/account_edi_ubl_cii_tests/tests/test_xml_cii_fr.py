# -*- coding: utf-8 -*-
from odoo.addons.account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestCIIFR(TestUBLCommon):

    @classmethod
    def setUpClass(cls,
                   chart_template_ref="l10n_fr.l10n_fr_pcg_chart_template",
                   #chart_template_ref=None,
                   edi_format_ref="account_edi_ubl_cii.facturx_cii",
                   ):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Rue Jean Jaurès, 42",
            'zip': "75000",
            'city': "Paris",
            'vat': 'FR05677404089',
            'country_id': cls.env.ref('base.fr').id,
            'bank_ids': [(0, 0, {'acc_number': 'FR15001559627230'})],
            'phone': '+1 (650) 555-0111',
            'email': "partner1@yourcompany.com",
            'ref': 'seller_ref',
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Rue Charles de Gaulle",
            'zip': "52330",
            'city': "Colombey-les-Deux-Églises",
            'vat': 'FR35562153452',
            'country_id': cls.env.ref('base.fr').id,
            'bank_ids': [(0, 0, {'acc_number': 'FR90735788866632'})],
            'ref': 'buyer_ref',
        })

        cls.tax_21 = cls.env['account.tax'].create({
            'name': 'tax_21',
            'amount_type': 'percent',
            'amount': 21,
            'type_tax_use': 'sale',
        })

        # remove this tax, otherwise, at import, this tax with children taxes is selected and the total is wrong
        cls.tax_armageddon.children_tax_ids.unlink()
        cls.tax_armageddon.unlink()

        cls.tax_20 = cls.env['account.tax'].create({
            'name': 'tax_20',
            'amount_type': 'percent',
            'amount': 20,
            'type_tax_use': 'sale',
        })

        cls.tax_12 = cls.env['account.tax'].create({
            'name': 'tax_12',
            'amount_type': 'percent',
            'amount': 12,
            'type_tax_use': 'sale',
        })

        cls.tax_55 = cls.env['account.tax'].create({
            'name': 'tax_55',
            'amount_type': 'percent',
            'amount': 5.5,
            'type_tax_use': 'sale',
        })

        cls.acc_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'FR15001559627231',
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
        # to force the company to be french
        res = super().setup_company_data(
            company_name,
            chart_template=chart_template,
            country_id=cls.env.ref("base.fr").id,
            phone='+1 (650) 555-0111',  # [BR-DE-6] "Seller contact telephone number" (BT-42) is required
            email="info@yourcompany.com",  # [BR-DE-7] The element "Seller contact email address" (BT-43) is required
        )
        return res

    ####################################################
    # Test export - import
    ####################################################

    def test_export_pdf(self):
        self.invoice.action_post()
        pdf_values = self.edi_format._get_embedding_to_invoice_pdf_values(self.invoice)
        self.assertEqual(pdf_values['name'], 'factur-x.xml')  # first, make sure the old factur-x is not installed !

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
                'INV_2017_01_0002_ubl_bis3.xml',
                'factur-x.xml',
            }
        )

    def test_export_import_invoice(self):
        invoice, xml_etree, xml_filename = self._export_invoice(
            self.partner_1,
            self.partner_2,
            xpaths='''    
            ''',
            expected_file='test_fr_out_invoice.xml',
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
        self.assertEqual(xml_filename, "factur-x.xml")
        self._import_invoice(invoice, xml_etree, xml_filename)

    def test_export_import_refund(self):
        invoice, xml_etree, xml_filename = self._export_invoice(
            self.partner_1,
            self.partner_2,
            xpaths='''
            ''',
            expected_file='test_fr_out_refund.xml',
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
        self.assertEqual(xml_filename, "factur-x.xml")
        self._import_invoice(invoice, xml_etree, xml_filename)

    ####################################################
    # Test import
    # files come from the official documentation of the FNFE (subdirectory: "5. FACTUR-X 1.0.06 - Examples")
    ####################################################

    def test_facturx_xml_import(self):
        subfolder = 'test_files/factur-x'
        self._import_invoice_from_file(subfolder=subfolder, filename='Facture_DOM_EN16931.pdf', amount_total=383.75,
                                       amount_tax=0)
        self._import_invoice_from_file(subfolder=subfolder, filename='Facture_FR_EN16931.pdf', amount_total=470.15,
                                       amount_tax=46.25)
        self._import_invoice_from_file(subfolder=subfolder, filename='Facture_UE_EN16931.pdf', amount_total=1453.76,
                                       amount_tax=0)
        # the 2 following files have the same pdf but one is labelled as an invoice and the other as a refund
        self._import_invoice_from_file(subfolder=subfolder, filename='Avoir_FR_type380_EN16931.pdf',
                                       amount_total=233.47, amount_tax=14.99, move_type='in_refund')
        self._import_invoice_from_file(subfolder=subfolder, filename='Avoir_FR_type381_EN16931.pdf',
                                       amount_total=233.47, amount_tax=14.99, move_type='in_refund')
        # basis quantity != 1 for one of the lines
        self._import_invoice_from_file(subfolder=subfolder, filename='Facture_F20220024_EN_16931_basis_quantity.pdf',
                                       amount_total=108, amount_tax=8)
        self._import_invoice_from_file(subfolder=subfolder, filename='Facture_F20220028_EN_16931_credit_note.pdf',
                                       amount_total=100, amount_tax=10, move_type='in_refund')
        # credit note labelled as an invoice with negative amounts
        self._import_invoice_from_file(subfolder=subfolder, filename='Facture_F20220029_EN_16931_K.pdf',
                                       amount_total=90, amount_tax=0, move_type='in_refund')

    def test_invoice_edi_xml(self):
        invoice = self._create_empty_vendor_bill()
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('account_edi_ubl_cii_tests', 'test_files', 'test_fr_out_invoice.xml', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 3164.22)

        self.create_invoice_from_file('account_edi_ubl_cii_tests', 'test_files', 'test_fr_out_invoice.xml')

        self.assertEqual(invoice.amount_total, 3164.22)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)
