from odoo.tests.common import Form, TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAddressFields(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tr_company = cls.env['res.company'].create({
            'name': 'TR Test Co',
            'country_id': cls.env.ref('base.tr').id
        })
        cls.env.ref('l10n_tr.chart_template_7b').try_loading(cls.tr_company)

        cls.us_company = cls.env['res.company'].create({
            'name': 'US Test Co',
            'country_id': cls.env.ref('base.us').id
        })
        cls.env.user.company_id = cls.tr_company

    def test_partner_create_update_with_neighborhood(self):
        """ Will test the compute and inverse methods of address fields when creating partner records. """
        turkey = self.env.ref('base.tr')
        Neighborhood = self.env['l10n_tr.neighborhood']
        Partner = self.env['res.partner']

        form1 = Form(Partner)
        form1.name = 'Test Address1'
        form1.country_id = turkey
        form1.l10n_tr_neighborhood_id = Neighborhood.search([('name', '=', 'MESTANZADE MAH')], limit=1)
        partner1 = form1.save()
        self.assertRecordValues(partner1, [{
            'l10n_tr_area_id': self.ref('l10n_tr.semt_01020_hukumet'),
            'city_id': self.ref('l10n_tr.ilce_01_seyhan'),
            'city': 'HÜKÜMET SEYHAN',
            'street2': 'MESTANZADE MAH',
            'zip': '01020',
        }])

        form2 = Form(Partner)
        form2.name = 'Test Address2'
        form2.country_id = turkey
        form2.l10n_tr_neighborhood_id = Neighborhood.search([('name', '=', 'ODUNKAPI MAH')], limit=1)
        partner2 = form2.save()
        self.assertRecordValues(partner2, [{
            'l10n_tr_area_id': self.ref('l10n_tr.semt_35260_konak'),
            'city_id': self.ref('l10n_tr.ilce_35_konak'),
            'city': 'KONAK',
            'street2': 'ODUNKAPI MAH',
            'zip': '35260',
        }])

        with Form(partner1) as form1:
            form1.l10n_tr_neighborhood_id = Neighborhood.search([('name', '=', 'ODUNKAPI MAH')], limit=1)

        self.assertRecordValues(partner1, [{
            'l10n_tr_area_id': self.ref('l10n_tr.semt_35260_konak'),
            'city_id': self.ref('l10n_tr.ilce_35_konak'),
            'city': 'KONAK',
            'street2': 'ODUNKAPI MAH',
            'zip': '35260',
            'state_id': self.ref('base.state_tr_35'),
        }])

        with Form(partner1) as form1:
            form1.state_id = self.env.ref('base.state_tr_05')
        self.assertRecordValues(partner1, [{
            'l10n_tr_area_id': False,
            'city_id': False,
            'city': '',
            'street2': '',
            'zip': ''
        }])

        with Form(partner2) as form2:
            form2.l10n_tr_area_id = self.env.ref('l10n_tr.semt_01020_hukumet')
        self.assertRecordValues(partner2, [{
            'l10n_tr_neighborhood_id': False,
            'city_id': self.ref('l10n_tr.ilce_01_seyhan'),
            'city': 'HÜKÜMET SEYHAN',
            'street2': '',
            'zip': '01020',
            'state_id': self.ref('base.state_tr_01'),
        }])

    def test_tr_fields_not_available_in_non_tr_companies(self):
        self.env.user.company_id = self.us_company
        with self.assertRaises(AssertionError,
                               msg="Turkish address fields should not be available in non TR companies."):
            with Form(self.env['res.partner']) as form:
                form.country_id = self.env.ref('base.tr')
                form.l10n_tr_neighborhood_id = self.env['l10n_tr.neighborhood'].search([], limit=1)

        with self.assertRaises(AssertionError,
                               msg="Turkish address fields should not be available in non TR companies."):
            with Form(self.env['res.partner']) as form:
                form.country_id = self.env.ref('base.tr')
                form.l10n_tr_area_id = self.env['l10n_tr.area'].search([], limit=1)
