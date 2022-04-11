# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os

from lxml import etree

from odoo import api, fields, models, tools
from odoo.modules import get_module_resource
from odoo.modules.module import get_resource_from_path, get_resource_path
from odoo.tools.convert import xml_import
from odoo.tools.misc import file_open
from odoo.tools.translate import TranslationFileReader


class ResetTemplateMixin(models.Model):
    _name = "reset.template.mixin"
    _description = 'Reset Template Mixin'

    template_fs = fields.Char(
        string='Template Filename', copy=False,
        help="""File from where the template originates. Useful to reset broken template.""")
    is_template_modified = fields.Boolean(string='Is Template Modified', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if 'install_filename' in self._context:
                # we store the relative path to the resource instead of the absolute path, if found
                # (it will be missing e.g. when importing data-only modules using base_import_module)
                path_info = get_resource_from_path(self._context['install_filename'])
                if path_info:
                    val['template_fs'] = '/'.join(path_info[0:2])
        return super().create(vals_list)

    def write(self, vals):
        vals['is_template_modified'] = vals.get('is_template_modified', True)
        return super().write(vals)

    # ------------------------------------------------------------
    # RESET TEMPLATE
    # ------------------------------------------------------------

    def _process_translation_data(self, trans_file, lang, xml_ids):
        """Populates the ir_translation table.
        :param trans_file: path to open a translation file
        :param lang: language code of the translations contained in `trans_file`
                     language must be present and activated in the database
        """
        with file_open(trans_file, mode='rb') as fileobj:
            fileformat = os.path.splitext(trans_file)[-1][1:].lower()
            reader = TranslationFileReader(fileobj, fileformat=fileformat)
            # Process a single PO (or POT) entry
            for row in reader:
                if row.get('imd_name') in xml_ids:
                    # copy Translation from Source to Destination object
                    self.env['ir.translation']._set_ids(
                        row['name'], 'model', lang, self._ids, row.get('value', ''), row['src'],
                    )

    def _override_translation_term(self, module_name, xml_ids):
        for code, _ in self.env['res.lang'].get_installed():
            lang_code = tools.get_iso_codes(code)
            base_lang_code = lang_code.split('_')[0] if '_' in lang_code else lang_code
            is_po_file_available = False
            # In case of sub languages (e.g fr_BE), load the base language first, (e.g fr.po) and
            # then load the main translation file (e.g fr_BE.po)

            # Step 1: reset translation terms with base language file
            base_trans_file = get_module_resource(module_name, 'i18n', base_lang_code + '.po')
            if base_trans_file:
                is_po_file_available = True
                self._process_translation_data(base_trans_file, code, xml_ids)

            # Step 2: reset translation file with main language file (can possibly override the
            # terms coming from the base language)
            trans_file = get_module_resource(module_name, 'i18n', lang_code + '.po')
            if trans_file:
                is_po_file_available = True
                self._process_translation_data(trans_file, code, xml_ids)

            # If no translation file available, unlink custom translated terms linked to template
            if not is_po_file_available:
                self.env['ir.translation'].search([
                    ('name', 'like', f'{self._name},%'),
                    ('res_id', '=', self.id),
                    ('lang', '=', code),
                    ('module', 'in', [module_name, False]),
                ]).unlink()

    def reset_template(self):
        """Resets the Template with values given in source file. We ignore the case of
        template being overridden in another modules because it is extremely less likely
        to happen. This method also tries to reset the translation terms for the current
        user lang (all langs are not supported due to costly file operation). """
        for template in self.filtered(lambda t: t.template_fs and t.is_template_modified):
            external_id = template.get_external_id().get(template.id)
            module, xml_id = external_id.split('.')
            fullpath = get_resource_path(*template.template_fs.split('/'))
            if fullpath:
                doc = etree.parse(fullpath)
                for rec in doc.xpath("//record[@id='%s'] | //record[@id='%s']" % (external_id, xml_id)):
                    obj = xml_import(template.env.cr, module, {}, mode='init', xml_filename=fullpath)
                    obj._tag_record(rec)
                    template._override_translation_term(module, [xml_id, external_id])
                    template.is_template_modified = False
