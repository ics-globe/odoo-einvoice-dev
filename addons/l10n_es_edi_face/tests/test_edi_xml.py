# coding: utf-8
import logging
import random
from base64 import b64encode
from datetime import datetime
from unittest.mock import patch

from freezegun import freeze_time
from lxml import etree

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEsEdiFaceCommon(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_es.account_chart_template_full',
                   edi_format_ref='l10n_es_edi_face.edi_es_face'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)
        cls.frozen_today = datetime(year=2023, month=1, day=1, hour=0, minute=0, second=0)

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        # ==== Company ====

        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.es').id,
            'street': "C. de Embajadores, 68-116",
            'state_id': cls.env.ref('base.state_es_m').id,
            'city': "Madrid",
            'zip': "12345",
            'vat': 'ES59962470K',
        })

        # ==== Business ====

        cls.partner_a.write({
            'vat': 'BE0477472701',
            'country_id': cls.env.ref('base.be').id,
            'city': "Namur",
            'street': "Rue de Bruxelles, 15000",
            'zip': "5000",
        })

        cls.partner_b.write({
            'vat': 'ESF35999705',
            'country_id': cls.env.ref('base.es').id,
            'street': "C. de Embajadores, 68-116",
            'state_id': cls.env.ref('base.state_es_m').id,
            'city': "Madrid",
            'zip': "12345",
        })

        cls.product_t = cls.env["product.product"].create({"name": "Test product"})
        cls.partner_t = cls.env["res.partner"].create({"name": "Test partner", "vat": "ESF35999705"})
        cls.password = "test"
        cls.certificate = cls.env["l10n_es_edi_face.certificate"].create({
            "company_id": cls.company_data['company'].id,
            "content": b64encode(file_open('l10n_es_edi_face/tests/data/certificate_test.pfx', 'rb').read()),
            "password": "test",
        })

        cls.nsmap = {
            'fe': "http://www.facturae.es/Facturae/2007/v3.1/Facturae",
            'ds': "http://www.w3.org/2000/09/xmldsig#",
            'xd': "http://www.w3.org/2000/09/xmldsig#",
            'xades': "http://uri.etsi.org/01903/v1.3.2#",
        }

    @classmethod
    def create_invoice(cls, **kwargs):
        return cls.env['account.move'].with_context(edi_test_mode=True).create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': cls.frozen_today.isoformat(),
            'date': cls.frozen_today.isoformat(),
            **kwargs,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'price_unit': 1000.0,
                **line_vals,
            }) for line_vals in kwargs.get('invoice_line_ids', [])],
        })


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiFaceXmls(TestEsEdiFaceCommon):
    def test_generate_signed_xml(self, signed=True):
        random.seed(42)

        ids = [f"id-{''.join(str(random.randint(0, 10)) for v in range(15))}" for i in range(10)]
        with freeze_time(self.frozen_today), \
                patch('odoo.addons.l10n_es_edi_face.models.account_edi_format.AccountEdiFaceFormat'), \
                patch('xades.utils.get_unique_id', ids.pop), \
                patch('datetime.datetime.now', lambda: self.frozen_today):
            tax = self.env['account.tax'].create({
                'name': "IVA 21% (Bienes)",
                'company_id': self.company_data['company'].id,
                'amount': 21.0,
                'price_include': False,
                'l10n_es_edi_face_tax_type': '01'
            })[0]
            invoice = self.create_invoice(
                    partner_id=self.partner_a.id,
                    invoice_line_ids=[
                        {'price_unit': 100.0, 'tax_ids': [tax.id]},
                        {'price_unit': 100.0, 'tax_ids': [tax.id]},
                        {'price_unit': 200.0, 'tax_ids': [tax.id]},
                    ],
            )
            invoice.action_post()
            generated_files = self._process_documents_web_services(invoice, {"es_face"})
            self.assertTrue(generated_files)
            xml_file = etree.XML(generated_files[0])
            with file_open(f"l10n_es_edi_face/tests/data/expected_{'' if signed else 'un'}signed_xml.xml",
                           'rb') as exp_f:
                data = etree.XML(exp_f.read())
            cleaner = self.env['account.edi.format'].l10n_es_edi_face_clean_xml
            self.assertEqual(cleaner(xml_file, False), cleaner(data, False))


    def test_generate_unsigned_xml(self):
        self.certificate.unlink()
        with self.assertRaises(UserError):
            self.test_generate_signed_xml(signed=False)
