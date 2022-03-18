# coding: utf-8
from odoo.tests import common, tagged


@tagged('-at_install', 'post_install')
class TestTheme(common.TransactionCase):

    def test_theme_remove_working(self):
        """ This test ensure theme can be removed.
        Theme removal is also the first step during theme installation.
        """
        theme_common_module = self.env['ir.module.module'].search([('name', '=', 'theme_default')])
        website = self.env['website'].get_current_website()
        website.theme_id = theme_common_module.id
        self.env['ir.module.module']._theme_remove(website)

    def test_02_disable_view(self):
        """This test ensure only one template header can be active at a time."""
        website_id = self.env['website'].browse(1)
        ThemeUtils = self.env['theme.utils'].with_context(website_id=website_id.id)

        ThemeUtils._reset_default_config()

        def _get_header_template_key():
            return self.env['ir.ui.view'].search([
                ('key', 'in', ThemeUtils._header_templates),
                ('website_id', '=', website_id.id),
            ]).key

        self.assertEqual(_get_header_template_key(), 'website.template_header_default',
                         "Only the default template should be active.")

        key = 'website.template_header_magazine'
        ThemeUtils.enable_view(key)
        self.assertEqual(_get_header_template_key(), key,
                         "Only one template can be active at a time.")

        key = 'website.template_header_hamburger'
        ThemeUtils.enable_view(key)
        self.assertEqual(_get_header_template_key(), key,
                         "Ensuring it works also for non default template.")

    def test_03_theme_website_menu_create(self):
        """ This method is simulating and ensuring everything goes fine when
        creating `theme.website.menu` records in theme.
        It especially checks the `parent_id` part, which can either be an
        existing `website.menu` or another `theme.website.menu` from the theme.
        It basically simulates the install of the following:

            <record id="test_theme.theme_menu" model="theme.website.menu">
                <field name="name">Theme Menu</field>
                <field name="url">/theme-menu</field>
                <field name="parent_id" ref="website.main_menu"/>
            </record>
            <record id="test_theme.theme_sub_menu" model="theme.website.menu">
                <field name="name">Theme Sub Menu</field>
                <field name="url">/theme-sub-menu</field>
                <field name="parent_id" ref="test_theme.theme_menu"/>
            </record>

        Then simulate a module upgrade after a change of `parent_id` in the XML
        files.
        """
        Website = self.env['website']
        Menu = self.env['website.menu']
        ThemeMenu = self.env['theme.website.menu']
        Imd = self.env['ir.model.data']

        website_1 = Website.create({'name': 'Website 1'})
        generic_main_menu = self.env.ref('website.main_menu')

        initial_menus = Menu.search([])

        # 1. Simulate a theme install with some `website.theme.menu`
        test_theme_module = self.env['ir.module.module'].create({'name': 'test_theme'})
        Imd.create({
            'module': 'base',
            'name': 'module_test_theme_module',
            'model': 'ir.module.module',
            'res_id': test_theme_module.id,
        })
        theme_menu = ThemeMenu.create({
            'name': 'Theme Menu',
            'url': '/theme-menu',
            # here parent is a website.menu
            'parent_id': f'{generic_main_menu._name},{generic_main_menu.id}',
        })
        theme_sub_menu = ThemeMenu.create({
            'name': 'Theme Sub Menu',
            'url': '/theme-sub-menu',
            # here parent is a theme.website.menu
            'parent_id': f'{theme_menu._name},{theme_menu.id}',
        })
        Imd.create({
            'module': 'test_theme',
            'name': 'theme_menu',
            'model': 'theme.website.menu',
            'res_id': theme_menu.id,
        })
        Imd.create({
            'module': 'test_theme',
            'name': 'theme_sub_menu',
            'model': 'theme.website.menu',
            'res_id': theme_sub_menu.id,
        })

        # 2. Ensure everything went correctly, regarding theme records
        # (`theme.website.menu`). The theme is not yet installed on a website
        self.assertEqual(theme_menu.parent_id, generic_main_menu, "The parent should be the referenced website.menu record")
        self.assertEqual(theme_sub_menu.parent_id, theme_menu, "The parent should be the other theme.website.menu")
        self.assertEqual(len(initial_menus), Menu.search_count([]), "No website.menu should have been created yet.")

        # 3. Load the theme on the website
        test_theme_module._theme_load(website_1)

        # 4. Ensure everything went correctly, regarding converting the theme
        # records to base model and applying it on the website
        new_menus = Menu.search([('id', 'not in', initial_menus.ids)])
        self.assertEqual(len(initial_menus) + 2, Menu.search_count([]),
                         "The 2 theme.website.menu should have been converted to website.menu on website_1")
        self.assertTrue(new_menus[0].website_id == new_menus[1].website_id == website_1,
                        "The menus should have received the correct website_id")
        self.assertEqual(new_menus[0].parent_id, website_1.menu_id,
                         "As the parent was `ref('website.main_menu')` it should have been created for the website's top level menu.")
        self.assertEqual(new_menus[1].parent_id, new_menus[0])

        # 5. Simulate theme update, ensure everything went correctly during the
        # update. Correct converted record should be updated.
        theme_sub_menu.parent_id = f'{generic_main_menu._name},{generic_main_menu.id}'
        test_theme_module._theme_load(website_1)
        self.assertEqual(new_menus[1].parent_id, website_1.menu_id)

        theme_menu.parent_id = f'{theme_sub_menu._name},{theme_sub_menu.id}'
        test_theme_module._theme_load(website_1)
        self.assertEqual(new_menus[0].parent_id, new_menus[1])
        self.assertEqual(len(initial_menus) + 2, Menu.search_count([]),
                         "Only the 2 website converted menus should have been created")
