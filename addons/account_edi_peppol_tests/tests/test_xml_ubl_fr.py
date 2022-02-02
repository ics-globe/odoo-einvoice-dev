# -*- coding: utf-8 -*-
from odoo.addons.account_edi_peppol_tests.tests.common import TestUBLCommon
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestUBLFR(TestUBLCommon):

    @classmethod
    def setUpClass(cls,
                   #chart_template_ref="l10n_fr.l10n_fr_pcg_chart_template",
                   chart_template_ref=None,
                   ):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Rue Jean Jaurès, 42",
            'zip': "75000",
            'city': "Paris",
            'vat': 'FR05677404089',
            'country_id': cls.env.ref('base.fr').id,
            'bank_ids': [(0, 0, {'acc_number': 'FR15001559627230'})],
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Rue Charles de Gaulle",
            'zip': "52330",
            'city': "Colombey-les-Deux-Églises",
            'vat': 'FR35562153452',
            'country_id': cls.env.ref('base.fr').id,
            'bank_ids': [(0, 0, {'acc_number': 'FR90735788866632'})],
        })

        cls.tax_21 = cls.env['account.tax'].create({
            'name': 'tax_21',
            'amount_type': 'percent',
            'amount': 21,
            'type_tax_use': 'sale',
        })

        cls.tax_12 = cls.env['account.tax'].create({
            'name': 'tax_12',
            'amount_type': 'percent',
            'amount': 12,
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
            company_name, chart_template=chart_template, country_id=cls.env.ref("base.fr").id)
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
                <xpath expr=".//*[local-name()='PaymentMeans']/*[local-name()='PaymentID']" position="replace">
                    <PaymentID>___ignore___</PaymentID>
                </xpath>
                <xpath expr=".//*[local-name()='AccountingSupplierParty']//*[local-name()='Contact']/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='AccountingCustomerParty']//*[local-name()='Contact']/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
            ''',
            expected_file='test_fr_out_invoice.xml',
            export_file='export_out_invoice_21.xml',
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'quantity': 10.0,
                    'price_unit': 990.0,
                    'discount': 10.0,
                    'tax_ids': [(6, 0, self.tax_21.ids)],
                },
                {
                    'quantity': 10.0,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_12.ids)],
                },
                {
                    'quantity': -1.0,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_12.ids)],
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
                <xpath expr=".//*[local-name()='AccountingSupplierParty']//*[local-name()='Contact']/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='AccountingCustomerParty']//*[local-name()='Contact']/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
            ''',
            expected_file='test_fr_out_refund.xml',
            export_file='export_out_refund_21.xml',
            move_type='out_refund',
            invoice_line_ids=[
                {
                    'quantity': 10.0,
                    'price_unit': 990.0,
                    'discount': 10.0,
                    'tax_ids': [(6, 0, self.tax_21.ids)],
                },
                {
                    'quantity': 10.0,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_12.ids)],
                },
                {
                    'quantity': -1.0,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_12.ids)],
                },
            ],
        )

        self._import_invoice(invoice, xml_etree, xml_filename)

    def test_export_pdf(self):
        # 231 ?
        self.invoice.action_post()
        pdf_values = self.edi_format._get_embedding_to_invoice_pdf_values(self.invoice)
        self.assertEqual(pdf_values['name'], 'peppol.xml')  # first, make sure factur-x is not installed !

    ####################################################
    # Test import
    ####################################################

    def test_invoice_edi_pdf(self):
        # pdf corresponds to partner_1 sending a bill to partner_2, and partner_2 uploading it
        invoice = self._create_empty_vendor_bill()
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('account_edi_peppol_tests', 'test_files', 'test_fr_in_invoice.pdf', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)

        self.assertEqual(invoice.amount_total, 391.94)

        self.create_invoice_from_file('account_edi_peppol_tests', 'test_files', 'test_fr_in_invoice.pdf')

        self.assertEqual(invoice.amount_total, 391.94)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)

    def test_invoice_edi_xml(self):
        invoice = self._create_empty_vendor_bill()
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('account_edi_peppol_tests', 'test_files', 'test_fr_out_invoice.xml', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 11789.1)  # see cbc:PayableAmount

        self.create_invoice_from_file('account_edi_peppol_tests', 'test_files', 'test_fr_out_invoice.xml')

        self.assertEqual(invoice.amount_total, 11789.1)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)
