# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from psycopg2 import IntegrityError
import io

from odoo.exceptions import AccessError, ValidationError
from odoo.tools import mute_logger, trans_load_data
from odoo.tools.translate import quote, unquote, xml_translate, html_translate
from odoo.tests.common import TransactionCase, BaseCase, new_test_user


class TranslationToolsTestCase(BaseCase):
    def assertItemsEqual(self, a, b, msg=None):
        self.assertEqual(sorted(a), sorted(b), msg)

    def test_quote_unquote(self):

        def test_string(str):
            quoted = quote(str)
            #print "\n1:", repr(str)
            #print "2:", repr(quoted)
            unquoted = unquote("".join(quoted.split('"\n"')))
            #print "3:", repr(unquoted)
            self.assertEqual(str, unquoted)

        test_string("""test \nall kinds\n \n o\r
         \\\\ nope\n\n"
         """)

        # The ones with 1+ backslashes directly followed by
        # a newline or literal N can fail... we would need a
        # state-machine parser to handle these, but this would
        # be much slower so it's better to avoid them at the moment
        self.assertRaises(AssertionError, quote, """test \nall kinds\n\no\r
         \\\\nope\n\n"
         """)

    def test_translate_xml_base(self):
        """ Test xml_translate() without formatting elements. """
        terms = []
        source = """<form string="Form stuff">
                        <h1>Blah blah blah</h1>
                        Put some more text here
                        <field name="foo"/>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah blah blah', 'Put some more text here'])

    def test_translate_xml_text(self):
        """ Test xml_translate() on plain text. """
        terms = []
        source = "Blah blah blah"
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms, [source])

    def test_translate_xml_unicode(self):
        """ Test xml_translate() on plain text with unicode characters. """
        terms = []
        source = u"Un heureux évènement"
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms, [source])

    def test_translate_xml_text_entity(self):
        """ Test xml_translate() on plain text with HTML escaped entities. """
        terms = []
        source = "Blah&amp;nbsp;blah&amp;nbsp;blah"
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms, [source])

    def test_translate_xml_inline1(self):
        """ Test xml_translate() with formatting elements. """
        terms = []
        source = """<form string="Form stuff">
                        <h1>Blah <i>blah</i> blah</h1>
                        Put some <b>more text</b> here
                        <field name="foo"/>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah <i>blah</i> blah', 'Put some <b>more text</b> here'])

    def test_translate_xml_inline2(self):
        """ Test xml_translate() with formatting elements embedding other elements. """
        terms = []
        source = """<form string="Form stuff">
                        <b><h1>Blah <i>blah</i> blah</h1></b>
                        Put <em>some <b>more text</b></em> here
                        <field name="foo"/>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah <i>blah</i> blah', 'Put <em>some <b>more text</b></em> here'])

    def test_translate_xml_inline3(self):
        """ Test xml_translate() with formatting elements without actual text. """
        terms = []
        source = """<form string="Form stuff">
                        <div>
                            <span class="before"/>
                            <h1>Blah blah blah</h1>
                            <span class="after">
                                <i class="hack"/>
                            </span>
                        </div>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', 'Blah blah blah'])

    def test_translate_xml_inline4(self):
        """ Test xml_translate() with inline elements with translated attrs only. """
        terms = []
        source = """<form string="Form stuff">
                        <div>
                            <label for="stuff"/>
                            <span class="fa fa-globe" title="Title stuff"/>
                        </div>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms,
            ['Form stuff', '<span class="fa fa-globe" title="Title stuff"/>'])

    def test_translate_xml_inline5(self):
        """ Test xml_translate() with inline elements with empty translated attrs only. """
        terms = []
        source = """<form string="Form stuff">
                        <div>
                            <label for="stuff"/>
                            <span class="fa fa-globe" title=""/>
                        </div>
                    </form>"""
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms, ['Form stuff'])

    def test_translate_xml_t(self):
        """ Test xml_translate() with t-* attributes. """
        terms = []
        source = """<t t-name="stuff">
                        stuff before
                        <span t-field="o.name"/>
                        stuff after
                    </t>"""
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms,
            ['stuff before', 'stuff after'])

    def test_translate_xml_off(self):
        """ Test xml_translate() with attribute translate="off". """
        terms = []
        source = """<div>
                        stuff before
                        <div t-translation="off">Do not translate this</div>
                        stuff after
                    </div>"""
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms,
            ['stuff before', 'stuff after'])

    def test_translate_xml_attribute(self):
        """ Test xml_translate() with <attribute> elements. """
        terms = []
        source = """<field name="foo" position="attributes">
                        <attribute name="string">Translate this</attribute>
                        <attribute name="option">Do not translate this</attribute>
                    </field>"""
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms,
            ['Translate this'])

    def test_translate_xml_a(self):
        """ Test xml_translate() with <a> elements. """
        terms = []
        source = """<t t-name="stuff">
                        <ul class="nav navbar-nav">
                            <li class="nav-item">
                                <a class="nav-link oe_menu_leaf" href="/web#menu_id=42&amp;action=54">
                                    <span class="oe_menu_text">Blah</span>
                                </a>
                            </li>
                        </ul>
                    </t>"""
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms,
            ['<span class="oe_menu_text">Blah</span>'])

    def test_translate_xml_with_namespace(self):
        """ Test xml_translate() on elements with namespaces. """
        terms = []
        # do not slit the long line below, otherwise the result will not match
        source = """<Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
                        <cbc:UBLVersionID t-esc="version_id"/>
                        <t t-foreach="[1, 2, 3, 4]" t-as="value">
                            Oasis <cac:Test t-esc="value"/>
                        </t>
                    </Invoice>"""
        result = xml_translate(terms.append, source)
        self.assertEqual(result, source)
        self.assertItemsEqual(terms, ['Oasis'])
        result = xml_translate(lambda term: term, source)
        self.assertEqual(result, source)

    def test_translate_xml_invalid_translations(self):
        """ Test xml_translate() with invalid translations. """
        source = """<form string="Form stuff">
                        <h1>Blah <i>blah</i> blah</h1>
                        Put some <b>more text</b> here
                        <field name="foo"/>
                    </form>"""
        translations = {
            "Put some <b>more text</b> here": "Mettre <b>plus de texte</i> ici",
        }
        expect = """<form string="Form stuff">
                        <h1>Blah <i>blah</i> blah</h1>
                        Mettre <b>plus de texte ici
                        </b><field name="foo"/>
                    </form>"""
        result = xml_translate(translations.get, source)
        self.assertEqual(result, expect)

    def test_translate_html(self):
        """ Test html_translate(). """
        source = """<blockquote>A <h2>B</h2> C</blockquote>"""
        result = html_translate(lambda term: term, source)
        self.assertEqual(result, source)

    def test_translate_html_i(self):
        """ Test xml_translate() and html_translate() with <i> elements. """
        source = """<p>A <i class="fa-check"></i> B</p>"""
        result = xml_translate(lambda term: term, source)
        self.assertEqual(result, """<p>A <i class="fa-check"/> B</p>""")
        result = html_translate(lambda term: term, source)
        self.assertEqual(result, source)


class TestLanguageInstall(TransactionCase):
    def test_language_install(self):
        fr = self.env['res.lang'].with_context(active_test=False).search([('code', '=', 'fr_FR')])
        self.assertTrue(fr)
        wizard = self.env['base.language.install'].create({'lang_ids': fr.ids})
        wizard.flush()

        # running the wizard calls _load_module_terms() to load PO files
        loaded = []

        def _load_module_terms(self, modules, langs, overwrite=False):
            loaded.append((modules, langs, overwrite))

        with patch('odoo.addons.base.models.ir_translation.IrTranslation._load_module_terms', _load_module_terms):
            wizard.lang_install()

        # _load_module_terms is called once with lang='fr_FR' and overwrite=True
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0][1], ['fr_FR'])
        self.assertEqual(loaded[0][2], True)


class TestTranslation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.env.ref('base.module_base')._update_translations(['fr_FR'])
        cls.customers = cls.env['res.partner.category'].create({'name': 'Customers'})

        cls.customers_xml_id = cls.customers.export_data(['id']).get('datas')[0][0]
        po_string = '''
        #. module: __export__
        #: model:res.partner.category,name:%s
        msgid "Customers"
        msgstr "Clients"
        ''' % cls.customers_xml_id
        with io.BytesIO(bytes(po_string, encoding='utf-8')) as f:
            f.name = 'dummy'
            trans_load_data(cls.env.cr, f, 'po', 'fr_FR', verbose=True, create_empty_translation=True, overwrite=True)

    def test_101_create_translated_record(self):
        category = self.customers.with_context({})
        self.assertEqual(category.name, 'Customers', "Error in basic name_get")

        category_fr = category.with_context({'lang': 'fr_FR'})
        self.assertEqual(category_fr.name, 'Clients', "Translation not found")

    def test_102_duplicate_record(self):
        category = self.customers.with_context({'lang': 'fr_FR'}).copy()

        category_no = category.with_context({})
        self.assertEqual(category_no.name, 'Customers', "Duplication did not set untranslated value")

        category_fr = category.with_context({'lang': 'fr_FR'})
        self.assertEqual(category_fr.name, 'Clients', "Did not found translation for initial value")

    def test_103_duplicate_record_fr(self):
        category = self.customers.with_context({'lang': 'fr_FR'}).copy({'name': 'Clients (copie)'})

        category_no = category.with_context({})
        self.assertEqual(category_no.name, 'Clients (copie)', "Duplication should set untranslated value")

        category_fr = category.with_context({'lang': 'fr_FR'})
        self.assertEqual(category_fr.name, 'Clients (copie)', "Did not used default value for translated value")

    def test_104_orderby_translated_field(self):
        """ Test search ordered by a translated field. """
        # create a category with a French translation
        padawans = self.env['res.partner.category'].create({'name': 'Padawans'})
        padawans_fr = padawans.with_context(lang='fr_FR')
        padawans_fr.write({'name': 'Apprentis'})
        # search for categories, and sort them by (translated) name
        categories = padawans_fr.search([('id', 'in', [self.customers.id, padawans.id])], order='name')
        self.assertEqual(categories.ids, [padawans.id, self.customers.id],
            "Search ordered by translated name should return Padawans (Apprentis) before Customers (Clients)")

    def test_107_duplicate_record_en(self):
        category = self.customers.with_context({'lang': 'en_US'}).copy()

        category_no = category.with_context({})
        self.assertEqual(category_no.name, 'Customers', "Duplication did not set untranslated value")

        category_fr = category.with_context({'lang': 'fr_FR'})
        self.assertEqual(category_fr.name, 'Clients', "Did not found translation for initial value")

    def test_108_search_en(self):
        CategoryEn = self.env['res.partner.category'].with_context(lang='en_US')
        category_equal = CategoryEn.search([('name', '=', 'Customers')])
        self.assertEqual(category_equal.id, self.customers.id, "Search with '=' doesn't work for English")
        category_ilike = CategoryEn.search([('name', 'ilike', 'stoMer')])
        self.assertIn(self.customers, category_ilike, "Search with 'ilike' doesn't work for English")

    def test_109_search_fr(self):
        CategoryFr = self.env['res.partner.category'].with_context(lang='fr_FR')
        category_equal = CategoryFr.search([('name', '=', 'Clients')])
        self.assertEqual(category_equal.id, self.customers.id, "Search with '=' doesn't work for non English")
        category_ilike = CategoryFr.search([('name', 'ilike', 'lIen')])
        self.assertIn(self.customers, category_ilike, "Search with 'ilike' doesn't work for non English")

    def test_110_search_es(self):
        self.env['res.lang']._activate_lang('es_ES')
        langs = self.env['res.lang'].get_installed()
        self.assertEqual([('en_US', 'English (US)'), ('fr_FR', 'French / Français'), ('es_ES', 'Spanish / Español')],
                         langs, "Test did not start with the expected languages")
        CategoryEs = self.env['res.partner.category'].with_context(lang='es_ES')
        category_equal = CategoryEs.search([('name', '=', 'Customers')])
        self.assertEqual(category_equal.id, self.customers.id, "Search with '=' should use the English name if the current language translation is not available")
        category_ilike = CategoryEs.search([('name', 'ilike', 'usTom')])
        self.assertIn(self.customers, category_ilike, "Search with 'ilike' should use the English name if the current language translation is not available")

class TestTranslationWrite(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env['res.partner.category'].create({'name': 'Reblochon'})
        cls.category_xml_id = cls.category.export_data(['id']).get('datas')[0][0]

    def test_03_fr_single(self):
        self.env['res.lang']._activate_lang('fr_FR')
        self.env['res.partner'].with_context(active_test=False).search([]).write({'lang': 'fr_FR'})
        self.env.ref('base.lang_en').active = False

        langs = self.env['res.lang'].get_installed()
        self.assertEqual([('fr_FR', 'French / Français')], langs, "Test did not started with expected languages")

        self.category.with_context(lang='fr_FR').write({'name': 'French Name'})
        source_name = self.category.with_context(lang=None).read(['name'])
        self.assertEqual(source_name[0]['name'], "French Name", "Reference field not updated")

        # read from the cache first
        self.assertEqual(self.category.with_context(lang=None).name, "French Name")
        self.assertEqual(self.category.with_context(lang='fr_FR').name, "French Name")

        # force save to database and clear the cache: force a clean state
        self.category.flush()
        self.category.invalidate_cache()

        # read from database
        self.assertEqual(self.category.with_context(lang=None).name, "French Name")
        self.assertEqual(self.category.with_context(lang='fr_FR').name, "French Name")

    def test_04_fr_multi(self):
        self.env['res.lang']._activate_lang('fr_FR')

        langs = self.env['res.lang'].get_installed()
        self.assertEqual([('en_US', 'English (US)'), ('fr_FR', 'French / Français')], langs,
            "Test did not started with expected languages")

        po_string = '''
        #. module: __export__
        #: model:res.partner.category,name:%s
        msgid "Reblochon"
        msgstr "Translated Name"
        ''' % self.category_xml_id
        with io.BytesIO(bytes(po_string, encoding='utf-8')) as f:
            f.name = 'dummy'
            trans_load_data(self.env.cr, f, 'po', 'en_US', verbose=True, create_empty_translation=True, overwrite=True)

        self.category.with_context(lang='fr_FR').write({'name': 'French Name'})
        self.category.with_context(lang='en_US').write({'name': 'English Name'})

        # read from the cache first
        self.assertEqual(self.category.with_context(lang=None).name, "English Name")
        self.assertEqual(self.category.with_context(lang='fr_FR').name, "French Name")
        self.assertEqual(self.category.with_context(lang='en_US').name, "English Name")

        # force save to database and clear the cache: force a clean state
        self.category.flush()
        self.category.invalidate_cache()

        # read from database
        self.assertEqual(self.category.with_context(lang=None).name, "English Name")
        self.assertEqual(self.category.with_context(lang='fr_FR').name, "French Name")
        self.assertEqual(self.category.with_context(lang='en_US').name, "English Name")

    def test_04_fr_multi_no_en(self):
        self.env['res.lang']._activate_lang('fr_FR')
        self.env['res.lang']._activate_lang('es_ES')
        self.env['res.partner'].with_context(active_test=False).search([]).write({'lang': 'fr_FR'})
        self.env.ref('base.lang_en').active = False

        langs = self.env['res.lang'].get_installed()
        self.assertEqual([('fr_FR', 'French / Français'), ('es_ES', 'Spanish / Español')], langs,
                         "Test did not start with the expected languages")

        self.category.with_context(lang='fr_FR').write({'name': 'French Name'})
        self.category.with_context(lang='es_ES').write({'name': 'Spanish Name'})
        self.category.with_context(lang=None).write({'name': 'None Name'})

        # read from the cache first
        self.assertEqual(self.category.with_context(lang='fr_FR').name, "French Name")
        self.assertEqual(self.category.with_context(lang='es_ES').name, "Spanish Name")
        self.assertEqual(self.category.with_context(lang=None).name, "None Name")

        # force save to database and clear the cache: force a clean state
        self.category.flush()
        self.category.invalidate_cache()

        # read from database
        self.assertEqual(self.category.with_context(lang='fr_FR').name, "French Name")
        self.assertEqual(self.category.with_context(lang='es_ES').name, "Spanish Name")
        self.assertEqual(self.category.with_context(lang=None).name, "None Name")

    def test_05_remove_multi_empty_string(self):
        self._test_05_remove_multi("")

    def test_05_remove_multi_false(self):
        self._test_05_remove_multi(False)

    def _test_05_remove_multi(self, empty_value):
        self.env['res.lang']._activate_lang('fr_FR')

        langs = self.env['res.lang'].get_installed()
        self.assertEqual([('en_US', 'English (US)'), ('fr_FR', 'French / Français')], langs,
            "Test did not started with expected languages")

        belgium = self.env.ref('base.be')
        # vat_label is translatable and not required
        belgium.with_context(lang='en_US').write({'vat_label': 'VAT'})
        belgium.with_context(lang='fr_FR').write({'vat_label': 'TVA'})

        # remove the value
        belgium.with_context(lang='fr_FR').write({'vat_label': empty_value})
        # should recover the initial value from db
        self.assertEqual(
            empty_value,
            belgium.with_context(lang='fr_FR').vat_label,
            "Value should be the empty_value"
        )
        self.assertEqual(
            empty_value,
            belgium.with_context(lang='en_US').vat_label,
            "Value should be the empty_value"
        )
        self.assertEqual(
            empty_value,
            belgium.with_context(lang=None).vat_label,
            "Value should be the empty_value"
        )

        belgium.with_context(lang='en_US').write({'vat_label': 'VAT'})
        belgium.with_context(lang='fr_FR').write({'vat_label': 'TVA'})

        # remove the value
        belgium.with_context(lang='en_US').write({'vat_label': empty_value})
        self.assertEqual(
            empty_value,
            belgium.with_context(lang='fr_FR').vat_label,
            "Value should be the empty_value"
        )
        self.assertEqual(
            empty_value,
            belgium.with_context(lang='en_US').vat_label,
            "Value should be the empty_value"
        )
        self.assertEqual(
            empty_value,
            belgium.with_context(lang=None).vat_label,
            "Value should be the empty_value"
        )

    def test_field_selection(self):
        """ Test translations of field selections. """
        field = self.env['ir.model']._fields['state']
        self.assertEqual([key for key, _ in field.selection], ['manual', 'base'])

        ir_field = self.env['ir.model.fields']._get('ir.model', 'state')
        ir_field = ir_field.with_context(lang='fr_FR')
        ir_field.selection_ids[0].name = 'Custo'
        ir_field.selection_ids[1].name = 'Pas touche!'

        fg = self.env['ir.model'].fields_get(['state'])
        self.assertEqual(fg['state']['selection'], field.selection)

        fg = self.env['ir.model'].with_context(lang='fr_FR').fields_get(['state'])
        self.assertEqual(fg['state']['selection'],
                         [('manual', 'Custo'), ('base', 'Pas touche!')])

    def test_load_views(self):
        """ Test translations of field descriptions in get_view(). """
        self.env['res.lang']._activate_lang('fr_FR')

        # add translation for the string of field ir.model.name
        ir_model_field = self.env['ir.model.fields']._get('ir.model', 'name')
        LABEL = "Description du Modèle"

        ir_model_field_xml_id = ir_model_field.export_data(['id']).get('datas')[0][0]
        po_string = '''
        #. module: __export__
        #: model:ir.model.fields,field_description:%s
        msgid "Name"
        msgstr "%s"
        ''' % (ir_model_field_xml_id, LABEL)
        with io.BytesIO(bytes(po_string, encoding='utf-8')) as f:
            f.name = 'dummy'
            trans_load_data(self.env.cr, f, 'po', 'fr_FR', verbose=True, create_empty_translation=True, overwrite=True)

        # check that fields_get() returns the expected label
        model = self.env['ir.model'].with_context(lang='fr_FR')
        info = model.fields_get(['name'])
        self.assertEqual(info['name']['string'], LABEL)

        # check that get_views() also returns the expected label
        info = model.get_views([(False, 'form')])
        self.assertEqual(info['models'][model._name]['name']['string'], LABEL)


class TestXMLTranslation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.env['res.lang']._activate_lang('nl_NL')
        cls.env.ref('base.module_base')._update_translations(['fr_FR', 'nl_NL'])

    def create_view(self, archf, terms, **kwargs):
        view = self.env['ir.ui.view'].create({
            'name': 'test',
            'model': 'res.partner',
            'arch': archf % terms,
        })
        # DLE P70: `_sync_terms_translations`, which delete translations for which there is no value, is called sooner than before
        # because it's called in `_write`, which is called by `flush`, which is called by the `search`.
        # `arch_db` is in `_write` instead of `create` because `arch_db` is the inverse of `arch`.
        # We need to flush `arch_db` before creating the translations otherwise the translation for which there is no value will be deleted,
        # while the `test_sync_update` specifically needs empty translations
        view.flush()

        view_xml_id = view.export_data(['id']).get('datas')[0][0]
        for lang, trans_terms in kwargs.items():
            po_string = ''
            for src, val in zip(terms, trans_terms):
                po_string += '''
                #. module: __export__
                #: model_terms:ir.ui.view,arch_db:%s
                msgid "%s"
                msgstr "%s"
                ''' % (view_xml_id, src, val)
            with io.BytesIO(bytes(po_string, encoding='utf-8')) as f:
                f.name = 'dummy'
                trans_load_data(self.env.cr, f, 'po', lang, verbose=True, create_empty_translation=True, overwrite=True)

        return view

    def test_copy(self):
        """ Create a simple view, fill in translations, and copy it. """
        archf = '<form string="%s"><div>%s</div><div>%s</div></form>'
        terms_en = ('Knife', 'Fork', 'Spoon')
        terms_fr = ('Couteau', 'Fourchette', 'Cuiller')
        view0 = self.create_view(archf, terms_en, fr_FR=terms_fr)

        env_en = self.env(context={})
        env_fr = self.env(context={'lang': 'fr_FR'})

        # check translated field
        self.assertEqual(view0.with_env(env_en).arch_db, archf % terms_en)
        self.assertEqual(view0.with_env(env_fr).arch_db, archf % terms_fr)

        # copy without lang
        view1 = view0.with_env(env_en).copy({})
        self.assertEqual(view1.with_env(env_en).arch_db, archf % terms_en)
        self.assertEqual(view1.with_env(env_fr).arch_db, archf % terms_fr)

        # copy with lang='fr_FR'
        view2 = view0.with_env(env_fr).copy({})
        self.assertEqual(view2.with_env(env_en).arch_db, archf % terms_en)
        self.assertEqual(view2.with_env(env_fr).arch_db, archf % terms_fr)

        # copy with lang='fr_FR' and translate=html_translate
        self.patch(type(self.env['ir.ui.view']).arch_db, 'translate', html_translate)
        view3 = view0.with_env(env_fr).copy({})
        self.assertEqual(view3.with_env(env_en).arch_db, archf % terms_en)
        self.assertEqual(view3.with_env(env_fr).arch_db, archf % terms_fr)

    # ???
    def test_spaces(self):
        """ Create translations where value has surrounding spaces. """
        archf = '<form string="%s"><div>%s</div><div>%s</div></form>'
        terms_en = ('Knife', 'Fork', 'Spoon')
        terms_fr = (' Couteau', 'Fourchette ', ' Cuiller ')
        self.create_view(archf, terms_en, fr_FR=terms_fr)

    def test_sync(self):
        """ Check translations after minor change in source terms. """
        archf = '<form string="X">%s</form>'
        terms_en = ('Bread and cheeze',)
        terms_fr = ('Pain et fromage',)
        terms_nl = ('Brood and kaas',)
        view = self.create_view(archf, terms_en, en_US=terms_en, fr_FR=terms_fr, nl_NL=terms_nl)

        env_nolang = self.env(context={})
        env_en = self.env(context={'lang': 'en_US'})
        env_fr = self.env(context={'lang': 'fr_FR'})
        env_nl = self.env(context={'lang': 'nl_NL'})

        self.assertEqual(view.with_env(env_nolang).arch_db, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch_db, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch_db, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch_db, archf % terms_nl)

        # modify source term in view (fixed type in 'cheeze')
        terms_en = ('Bread and cheese',)
        view.with_env(env_en).write({'arch_db': archf % terms_en})

        # check whether translations have been synchronized
        # self.assertEqual(view.with_env(env_nolang).arch_db, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch_db, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch_db, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch_db, archf % terms_nl)

        view = self.create_view(archf, terms_fr, en_US=terms_en, fr_FR=terms_fr, nl_NL=terms_nl)
        # modify source term in view in another language with close term
        new_terms_fr = ('Pains et fromage',)
        view.with_env(env_fr).write({'arch_db': archf % new_terms_fr})

        # check whether translations have been synchronized
        # ???
        # self.assertEqual(view.with_env(env_nolang).arch_db, archf % new_terms_fr)
        self.assertEqual(view.with_env(env_en).arch_db, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch_db, archf % new_terms_fr)
        self.assertEqual(view.with_env(env_nl).arch_db, archf % terms_nl)

    def test_sync_xml(self):
        """ Check translations of 'arch' after xml tags changes in source terms. """
        archf = '<form string="X">%s<div>%s</div></form>'
        terms_en = ('Bread and cheese', 'Fork')
        terms_fr = ('Pain et fromage', 'Fourchette')
        terms_nl = ('Brood and kaas', 'Vork')
        view = self.create_view(archf, terms_en, en_US=terms_en, fr_FR=terms_fr, nl_NL=terms_nl)

        env_nolang = self.env(context={})
        env_en = self.env(context={'lang': 'en_US'})
        env_fr = self.env(context={'lang': 'fr_FR'})
        env_nl = self.env(context={'lang': 'nl_NL'})

        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_nl)

        # modify source term in view (add css style)
        terms_en = ('Bread <span style="font-weight:bold">and</span> cheese', 'Fork')
        view.with_env(env_en).write({'arch': archf % terms_en})

        # check whether translations have been kept
        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % terms_fr)
        self.assertEqual(view.with_env(env_nl).arch, archf % terms_nl)

        # modify source term in view (actual text change)
        terms_en = ('Bread <span style="font-weight:bold">and</span> butter', 'Fork')
        view.with_env(env_en).write({'arch': archf % terms_en})

        # check whether translations have been reset
        self.assertEqual(view.with_env(env_nolang).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_en).arch, archf % terms_en)
        self.assertEqual(view.with_env(env_fr).arch, archf % (terms_en[0], terms_fr[1]))
        self.assertEqual(view.with_env(env_nl).arch, archf % (terms_en[0], terms_nl[1]))

    def test_cache_consistency(self):
        view = self.env["ir.ui.view"].create({
            "name": "test_translate_xml_cache_invalidation",
            "model": "res.partner",
            "arch": "<form><b>content</b></form>",
        })
        view_fr = view.with_context({"lang": "fr_FR"})
        self.assertIn("<b>", view.arch_db)
        self.assertIn("<b>", view_fr.arch_db)

        # write with no lang, and check consistency in other languages
        view.write({"arch_db": "<form><i>content</i></form>"})
        self.assertIn("<i>", view.arch_db)
        self.assertIn("<i>", view_fr.arch_db)
