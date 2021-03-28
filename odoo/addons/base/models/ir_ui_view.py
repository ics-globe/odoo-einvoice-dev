# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import collections
import datetime
import fnmatch
import inspect
import json
import logging
import math
import pprint
import re
import time
import uuid
import warnings

from dateutil.relativedelta import relativedelta

import werkzeug, werkzeug.urls
from lxml import etree
from lxml.etree import LxmlError
from lxml.builder import E

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, AccessError
from odoo.http import request
from odoo.modules.module import get_resource_from_path, get_resource_path
from odoo.tools import config, ConstantMapping, get_diff, pycompat, apply_inheritance_specs, locate_node
from odoo.tools.convert import _fix_multiple_roots
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools import safe_eval, lazy_property, frozendict
from odoo.tools.view_validation import valid_view, get_variable_names, get_domain_identifiers, get_dict_asts
from odoo.tools.translate import xml_translate, TRANSLATED_ATTRS
from odoo.tools.image import image_data_uri
from odoo.models import check_method_name
from odoo.osv.expression import expression

_logger = logging.getLogger(__name__)

MOVABLE_BRANDING = ['data-oe-model', 'data-oe-id', 'data-oe-field', 'data-oe-xpath', 'data-oe-source-id']


def quick_eval(expr, globals_dict):
    """ Functionally identical to safe_eval(), but optimized with special-casing. """
    # most (~95%) elements are 1/True/0/False
    if expr == '1':
        return 1
    if expr == 'True':
        return True
    if expr == '0':
        return 0
    if expr == 'False':
        return False
    return safe_eval.safe_eval(expr, globals_dict)


def att_names(name):
    yield name
    yield f"t-att-{name}"
    yield f"t-attf-{name}"


def transfer_field_to_modifiers(field, modifiers):
    default_values = {}
    state_exceptions = {}

    for attr in ('invisible', 'readonly', 'required'):
        state_exceptions[attr] = []
        default_values[attr] = bool(getattr(field, attr))

    for state, modifs in (field.states or {}).items():
        for modif in modifs:
            if default_values[modif[0]] != modif[1]:
                state_exceptions[modif[0]].append(state)

    for attr, default_value in default_values.items():
        if state_exceptions[attr]:
            modifiers[attr] = [("state", "not in" if default_value else "in", state_exceptions[attr])]
        elif default_value:
            modifiers[attr] = default_value


def transfer_node_to_modifiers(node, modifiers, context=None):
    # Don't deal with groups, it is done by check_group().
    # Need the context to evaluate the invisible attribute on tree views.
    # For non-tree views, the context shouldn't be given.
    if node.get('attrs'):
        attrs = node.get('attrs').strip()
        modifiers.update(ast.literal_eval(attrs))

    if node.get('states'):
        if 'invisible' in modifiers and isinstance(modifiers['invisible'], list):
            # TODO combine with AND or OR, use implicit AND for now.
            modifiers['invisible'].append(('state', 'not in', node.get('states').split(',')))
        else:
            modifiers['invisible'] = [('state', 'not in', node.get('states').split(','))]

    for attr in ('invisible', 'readonly', 'required'):
        value_str = node.get(attr)
        if value_str:
            value = bool(safe_eval.safe_eval(value_str, {'context': context or {}}))
            if value or (attr in modifiers):
                # Don't set the attribute to False if a dynamic value was
                # provided (i.e. a domain from attrs or states).
                modifiers[attr] = value


def transfer_modifiers_to_node(modifiers, node):
    if modifiers:
        node.set('modifiers', json.dumps(modifiers))


def keep_query(*keep_params, **additional_params):
    """
    Generate a query string keeping the current request querystring's parameters specified
    in ``keep_params`` and also adds the parameters specified in ``additional_params``.

    Multiple values query string params will be merged into a single one with comma seperated
    values.

    The ``keep_params`` arguments can use wildcards too, eg:

        keep_query('search', 'shop_*', page=4)
    """
    if not keep_params and not additional_params:
        keep_params = ('*',)
    params = additional_params.copy()
    qs_keys = list(request.httprequest.args) if request else []
    for keep_param in keep_params:
        for param in fnmatch.filter(qs_keys, keep_param):
            if param not in additional_params and param in qs_keys:
                params[param] = request.httprequest.args.getlist(param)
    return werkzeug.urls.url_encode(params)

# class used to check if field expressions (e.g. parent.field_name) exists in
# the view with an optimistic approach: we expect the field to be in the view
# composed by direct ancestors only (mode=='ancestors). If not, we load the
# full view with all inheritancies (mode=='full')
class field_validator:
    def __init__(self, obj, root, view_ids, root_view):
        self.env = obj.env
        self.root = root
        self.root_view = root_view
        self.model = obj.model
        self.view_ids = view_ids
        self.obj = obj
        self.mode = None         # ancestors, all
        self.fields = {}         # {(...model_of_parent, model): 'field_name'}
        self.fget = {}
        self.buttons = []

    # fill in self.fields with all the fields contained in the view self.root
    def _load_fields(self):
        models = (self.model,)
        self.fields = collections.defaultdict(list)
        for event, field in etree.iterwalk(self.root, ('start','end'), tag=("field", "groupby", "searchpanel")):
            if field.tag=="searchpanel":
                if event=='start':
                    models += (models[-1], )
                else:
                    models = models[:-1]
                continue
            fname = field.attrib.get('name')
            if event=='start':
                self.fields[tuple(models)].append(fname)
                if field.attrib.get('id'):
                    self.fields[tuple(models)].append(field.attrib.get('id'))
                comodel = None
                f = self.env[models[-1]]._fields.get(fname)
                if f and hasattr(f, 'comodel_name'):
                    comodel = f.comodel_name
                models += (comodel, )
            else:
                models = models[:-1]

    # load the full view, with all inheritancies in self.root
    def _load_full_view(self):
        views = self.root_view.get_inheriting_views_arch(self.view_ids)
        self.obj.browse(views.keys()).mapped('arch_db')
        self.root = self.root_view._get_node(views)

    def _has_fields(self, models, name):
        while name.startswith('parent.'):
            if not len(models):
                return False
            models = models[:-1]
            name = name[7:]
        return (name=='id') or (name in self.fields.get(tuple(models), {}))

    def field_get(self, model, name):
        if model._name not in self.fget:
            self.fget[model._name] = model.fields_get(attributes=['relation'])
        return self.fget[model._name].get(name, None)

    def has_fields(self, models, fields, node):
        models = [x._name for x in models]
        for name in fields:
            while not self._has_fields(models, name):
                if self.mode == None:                       # load fields from view based on ancestors
                    self._load_fields()
                    self.mode = 'ancestors'
                elif self.mode == 'ancestors':              # load fields from the full view
                    self._load_full_view()
                    self._load_fields()
                    self.mode = 'full'
                else:
                    msg = _(
                        'Field "%(field_name)s" does not exist in model "%(model_name)s"',
                        field_name=name, model_name=models[-1],
                    )
                    self.obj._raise_view_error(msg, node)
        return True


class ViewCustom(models.Model):
    _name = 'ir.ui.view.custom'
    _description = 'Custom View'
    _order = 'create_date desc'  # search(limit=1) should return the last customization

    ref_id = fields.Many2one('ir.ui.view', string='Original View', index=True, required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', index=True, required=True, ondelete='cascade')
    arch = fields.Text(string='View Architecture', required=True)

    def name_get(self):
        return [(rec.id, rec.user_id.name) for rec in self]

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if name:
            return self._search([('user_id', operator, name)] + (args or []), limit=limit, access_rights_uid=name_get_uid)
        return super(ViewCustom, self)._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    def _auto_init(self):
        res = super(ViewCustom, self)._auto_init()
        tools.create_index(self._cr, 'ir_ui_view_custom_user_id_ref_id',
                           self._table, ['user_id', 'ref_id'])
        return res


def _hasclass(context, *cls):
    """ Checks if the context node has all the classes passed as arguments
    """
    node_classes = set(context.context_node.attrib.get('class', '').split())
    return node_classes.issuperset(cls)


def get_view_arch_from_file(filepath, xmlid):
    module, view_id = xmlid.split('.')

    xpath = f"//*[@id='{xmlid}' or @id='{view_id}']"
    # when view is created from model with inheritS of ir_ui_view, the
    # xmlid has been suffixed by '_ir_ui_view'. We need to also search
    # for views without this prefix.
    if view_id.endswith('_ir_ui_view'):
        # len('_ir_ui_view') == 11
        xpath = xpath[:-1] + f" or @id='{xmlid[:-11]}' or @id='{view_id[:-11]}']"

    document = etree.parse(filepath)
    for node in document.xpath(xpath):
        if node.tag == 'record':
            field_arch = node.find('field[@name="arch"]')
            if field_arch is not None:
                _fix_multiple_roots(field_arch)
                inner = ''.join(
                    etree.tostring(child, encoding='unicode')
                    for child in field_arch.iterchildren()
                )
                return field_arch.text + inner

            field_view = node.find('field[@name="view_id"]')
            if field_view is not None:
                ref_module, _, ref_view_id = field_view.attrib.get('ref').rpartition('.')
                ref_xmlid = f'{ref_module or module}.{ref_view_id}'
                return get_view_arch_from_file(filepath, ref_xmlid)

            return None

        elif node.tag == 'template':
            # The following dom operations has been copied from convert.py's _tag_template()
            if not node.get('inherit_id'):
                node.set('t-name', xmlid)
                node.tag = 't'
            else:
                node.tag = 'data'
            node.attrib.pop('id', None)
            return etree.tostring(node, encoding='unicode')

    _logger.warning("Could not find view arch definition in file '%s' for xmlid '%s'", filepath, xmlid)
    return None


xpath_utils = etree.FunctionNamespace(None)
xpath_utils['hasclass'] = _hasclass

TRANSLATED_ATTRS_RE = re.compile(r"@(%s)\b" % "|".join(TRANSLATED_ATTRS))
WRONGCLASS = re.compile(r"(@class\s*=|=\s*@class|contains\(@class)")


class View(models.Model):
    _name = 'ir.ui.view'
    _description = 'View'
    _order = "priority,name,id"

    name = fields.Char(string='View Name', required=True)
    model = fields.Char(index=True)
    key = fields.Char()
    priority = fields.Integer(string='Sequence', default=16, required=True)
    type = fields.Selection([('tree', 'Tree'),
                             ('form', 'Form'),
                             ('graph', 'Graph'),
                             ('pivot', 'Pivot'),
                             ('calendar', 'Calendar'),
                             ('gantt', 'Gantt'),
                             ('kanban', 'Kanban'),
                             ('search', 'Search'),
                             ('qweb', 'QWeb')], string='View Type')
    arch = fields.Text(compute='_compute_arch', inverse='_inverse_arch', string='View Architecture',
                       help="""This field should be used when accessing view arch. It will use translation.
                               Note that it will read `arch_db` or `arch_fs` if in dev-xml mode.""")
    arch_base = fields.Text(compute='_compute_arch_base', inverse='_inverse_arch_base', string='Base View Architecture',
                            help="This field is the same as `arch` field without translations")
    arch_db = fields.Text(string='Arch Blob', translate=xml_translate,
                          help="This field stores the view arch.")
    arch_fs = fields.Char(string='Arch Filename', help="""File from where the view originates.
                                                          Useful to (hard) reset broken views or to read arch from file in dev-xml mode.""")
    arch_updated = fields.Boolean(string='Modified Architecture')
    arch_prev = fields.Text(string='Previous View Architecture', help="""This field will save the current `arch_db` before writing on it.
                                                                         Useful to (soft) reset a broken view.""", prefetch=False)
    inherit_id = fields.Many2one('ir.ui.view', string='Inherited View', ondelete='restrict', index=True)
    inherit_children_ids = fields.One2many('ir.ui.view', 'inherit_id', string='Views which inherit from this one')
    field_parent = fields.Char(string='Child Field')
    model_data_id = fields.Many2one('ir.model.data', string="Model Data",
                                    compute='_compute_model_data_id', search='_search_model_data_id')
    xml_id = fields.Char(string="External ID", compute='_compute_xml_id',
                         help="ID of the view defined in xml file")
    groups_id = fields.Many2many('res.groups', 'ir_ui_view_group_rel', 'view_id', 'group_id',
                                 string='Groups', help="If this field is empty, the view applies to all users. Otherwise, the view applies to the users of those groups only.")
    mode = fields.Selection([('primary', "Base view"), ('extension', "Extension View")],
                            string="View inheritance mode", default='primary', required=True,
                            help="""Only applies if this view inherits from an other one (inherit_id is not False/Null).

* if extension (default), if this view is requested the closest primary view
is looked up (via inherit_id), then all views inheriting from it with this
view's model are applied
* if primary, the closest primary view is fully resolved (even if it uses a
different model than this one), then this view's inheritance specs
(<xpath/>) are applied, and the result is used as if it were this view's
actual arch.
""")
    active = fields.Boolean(default=True,
                            help="""If this view is inherited,
* if True, the view always extends its parent
* if False, the view currently does not extend its parent but can be enabled
         """)

    @api.depends('arch_db', 'arch_fs', 'arch_updated')
    @api.depends_context('read_arch_from_file', 'lang')
    def _compute_arch(self):
        def resolve_external_ids(arch_fs, view_xml_id):
            def replacer(m):
                xmlid = m.group('xmlid')
                if '.' not in xmlid:
                    xmlid = '%s.%s' % (view_xml_id.split('.')[0], xmlid)
                return m.group('prefix') + str(self.env['ir.model.data']._xmlid_to_res_id(xmlid))
            return re.sub(r'(?P<prefix>[^%])%\((?P<xmlid>.*?)\)[ds]', replacer, arch_fs)

        for view in self:
            arch_fs = None
            read_file = self._context.get('read_arch_from_file') or \
                ('xml' in config['dev_mode'] and not view.arch_updated)
            if read_file and view.arch_fs and (view.xml_id or view.key):
                xml_id = view.xml_id or view.key
                # It is safe to split on / herebelow because arch_fs is explicitely stored with '/'
                fullpath = get_resource_path(*view.arch_fs.split('/'))
                if fullpath:
                    arch_fs = get_view_arch_from_file(fullpath, xml_id)
                    # replace %(xml_id)s, %(xml_id)d, %%(xml_id)s, %%(xml_id)d by the res_id
                    if arch_fs:
                        arch_fs = resolve_external_ids(arch_fs, xml_id).replace('%%', '%')
                        if self.env.context.get('lang'):
                            tr = self._fields['arch_db'].get_trans_func(view)
                            arch_fs = tr(view.id, arch_fs)
                else:
                    _logger.warning("View %s: Full path [%s] cannot be found.", xml_id, view.arch_fs)
                    arch_fs = False
            view.arch = pycompat.to_text(arch_fs or view.arch_db)

    def _inverse_arch(self):
        for view in self:
            data = dict(arch_db=view.arch)
            if 'install_filename' in self._context:
                # we store the relative path to the resource instead of the absolute path, if found
                # (it will be missing e.g. when importing data-only modules using base_import_module)
                path_info = get_resource_from_path(self._context['install_filename'])
                if path_info:
                    data['arch_fs'] = '/'.join(path_info[0:2])
                    data['arch_updated'] = False
            view.write(data)
        # the field 'arch' depends on the context and has been implicitly
        # modified in all languages; the invalidation below ensures that the
        # field does not keep an old value in another environment
        self.invalidate_cache(['arch'], self._ids)

    @api.depends('arch')
    @api.depends_context('read_arch_from_file')
    def _compute_arch_base(self):
        # 'arch_base' is the same as 'arch' without translation
        for view, view_wo_lang in zip(self, self.with_context(lang=None)):
            view.arch_base = view_wo_lang.arch

    def _inverse_arch_base(self):
        for view, view_wo_lang in zip(self, self.with_context(lang=None)):
            view_wo_lang.arch = view.arch_base

    def reset_arch(self, mode='soft'):
        """ Reset the view arch to its previous arch (soft) or its XML file arch
        if exists (hard).
        """
        for view in self:
            arch = False
            if mode == 'soft':
                arch = view.arch_prev
            elif mode == 'hard' and view.arch_fs:
                arch = view.with_context(read_arch_from_file=True, lang=None).arch
            if arch:
                # Don't save current arch in previous since we reset, this arch is probably broken
                view.with_context(no_save_prev=True, lang=None).write({'arch_db': arch})

    @api.depends('write_date')
    def _compute_model_data_id(self):
        # get the first ir_model_data record corresponding to self
        for view in self:
            view.model_data_id = False
        domain = [('model', '=', 'ir.ui.view'), ('res_id', 'in', self.ids)]
        for data in self.env['ir.model.data'].sudo().search_read(domain, ['res_id'], order='id desc'):
            view = self.browse(data['res_id'])
            view.model_data_id = data['id']

    def _search_model_data_id(self, operator, value):
        name = 'name' if isinstance(value, str) else 'id'
        domain = [('model', '=', 'ir.ui.view'), (name, operator, value)]
        data = self.env['ir.model.data'].sudo().search(domain)
        return [('id', 'in', data.mapped('res_id'))]

    def _compute_xml_id(self):
        xml_ids = collections.defaultdict(list)
        domain = [('model', '=', 'ir.ui.view'), ('res_id', 'in', self.ids)]
        for data in self.env['ir.model.data'].sudo().search_read(domain, ['module', 'name', 'res_id']):
            xml_ids[data['res_id']].append("%s.%s" % (data['module'], data['name']))
        for view in self:
            view.xml_id = xml_ids.get(view.id, [''])[0]

    def _check_xml_inheritance(self, arch):
        """ Check whether view inheritance is based on translated attribute. """
        for node in arch.xpath('//*[@position]'):
            # inheritance may not use a translated attribute as selector
            if node.tag == 'xpath':
                match = TRANSLATED_ATTRS_RE.search(node.get('expr', ''))
                if match:
                    message = "View inheritance may not use attribute %r as a selector." % match.group(1)
                    self._raise_view_error(message, node)
                if WRONGCLASS.search(node.get('expr', '')):
                    _logger.warning(
                        "Error-prone use of @class in view %s (%s): use the "
                        "hasclass(*classes) function to filter elements by "
                        "their classes", self.name, self.xml_id
                    )
            else:
                for attr in TRANSLATED_ATTRS:
                    if node.get(attr):
                        message = "View inheritance may not use attribute %r as a selector." % attr
                        self._raise_view_error(message, node)
        return True

    @api.constrains('arch_db')
    def _check_xml(self):
        for view in self:
            if not view.active:
                continue

            # verify the view is valid xml and that the inheritance resolves
            node = etree.fromstring(view.arch)
            tocheck = [node]
            if view.inherit_id:
                view._check_xml_inheritance(node)
                if node.tag == "data":
                    tocheck = [y for x in node for y in x if x.attrib.get('position') != 'attributes']
                else:
                    tocheck = [x for x in node if node.attrib.get('position') != 'attributes']

            # Build a view with direct dependencies only
            views = {view.id: []}
            root_view = view
            while root_view.inherit_id:
                views[root_view.inherit_id.id] = [root_view.id]
                root_view = root_view.inherit_id

            # get all views
            # views = root.get_inheriting_views_arch(views.keys())

            self.browse(views.keys()).mapped('arch_db')
            root = root_view._get_node(views, {view.id: node})

            # TODO: check if this is necessary? and we can reduce the deepness of inheritancy to direct view only
            if view.type == 'qweb':
                continue

            fval = field_validator(view, root, views.keys(), root_view)

            # the inherited node are now embeded in the view, we can validate those nodes only
            for node in tocheck:
                models = [self.env[view.model]]
                for node_field in node.iterancestors('field', 'groupby', 'searchpanel'):
                    if node_field.get("position"):
                        # a node with a position attribute inside another node with a position attribute
                        # e.g. a position="move" case
                        # <field name="state" position="before">
                        #     <xpath expr="//div[hasclass('alert-info')]" position="move"/>
                        # </field>
                        continue
                    elif node_field.tag == 'searchpanel':
                        # a search panel defines a new namespace for fields inside
                        models.append(models[-1])
                    else:
                        field = node_field.attrib.get('name')
                        models.append(self.env[models[-1]._fields.get(field).comodel_name])
                view._check_node(node, models, fval)
        return True

    @api.constrains('type', 'groups_id', 'inherit_id')
    def _check_groups(self):
        for view in self:
            if (view.type == 'qweb' and
                view.groups_id and
                view.inherit_id and
                view.mode != 'primary'):
                raise ValidationError(_("Inherited Qweb view cannot have 'Groups' define on the record. Use 'groups' attributes inside the view definition"))

    @api.constrains('inherit_id')
    def _check_000_inheritance(self):
        # NOTE: constraints methods are check alphabetically. Always ensure this method will be
        #       called before other constraint methods to avoid infinite loop in `_get_combined_arch`.
        if not self._check_recursion(parent='inherit_id'):
            raise ValidationError(_('You cannot create recursive inherited views.'))

    _sql_constraints = [
        ('inheritance_mode',
         "CHECK (mode != 'extension' OR inherit_id IS NOT NULL)",
         "Invalid inheritance mode: if the mode is 'extension', the view must"
         " extend an other view"),
        ('qweb_required_key',
         "CHECK (type != 'qweb' OR key IS NOT NULL)",
         "Invalid key: QWeb view should have a key"),
    ]

    def _auto_init(self):
        res = super(View, self)._auto_init()
        tools.create_index(self._cr, 'ir_ui_view_model_type_inherit_id',
                           self._table, ['model', 'inherit_id'])
        return res

    def _compute_defaults(self, values):
        if 'inherit_id' in values:
            # Do not automatically change the mode if the view already has an inherit_id,
            # and the user change it to another.
            if not values['inherit_id'] or all(not view.inherit_id for view in self):
                values.setdefault('mode', 'extension' if values['inherit_id'] else 'primary')
        return values

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if not values.get('type'):
                if values.get('inherit_id'):
                    values['type'] = self.browse(values['inherit_id']).type
                else:

                    try:
                        if not values.get('arch') and not values.get('arch_base'):
                            raise ValidationError(_('Missing view architecture.'))
                        values['type'] = etree.fromstring(values.get('arch') or values.get('arch_base')).tag
                    except LxmlError:
                        # don't raise here, the constraint that runs `self._check_xml` will
                        # do the job properly.
                        pass
            if not values.get('key') and values.get('type') == 'qweb':
                values['key'] = "gen_key.%s" % str(uuid.uuid4())[:6]
            if not values.get('name'):
                values['name'] = "%s %s" % (values.get('model'), values['type'])
            # Create might be called with either `arch` (xml files), `arch_base` (form view) or `arch_db`.
            values['arch_prev'] = values.get('arch_base') or values.get('arch_db') or values.get('arch')
            # write on arch: bypass _inverse_arch()
            if 'arch' in values:
                values['arch_db'] = values.pop('arch')
                if 'install_filename' in self._context:
                    # we store the relative path to the resource instead of the absolute path, if found
                    # (it will be missing e.g. when importing data-only modules using base_import_module)
                    path_info = get_resource_from_path(self._context['install_filename'])
                    if path_info:
                        values['arch_fs'] = '/'.join(path_info[0:2])
                        values['arch_updated'] = False
            values.update(self._compute_defaults(values))

        self.clear_caches()
        result = super(View, self.with_context(ir_ui_view_partial_validation=True)).create(vals_list)
        return result.with_env(self.env)

    def write(self, vals):
        # Keep track if view was modified. That will be useful for the --dev mode
        # to prefer modified arch over file arch.
        if 'arch_updated' not in vals and ('arch' in vals or 'arch_base' in vals) and 'install_filename' not in self._context:
            vals['arch_updated'] = True

        # drop the corresponding view customizations (used for dashboards for example), otherwise
        # not all users would see the updated views
        custom_view = self.env['ir.ui.view.custom'].search([('ref_id', 'in', self.ids)])
        if custom_view:
            custom_view.unlink()

        self.clear_caches()
        if 'arch_db' in vals and not self.env.context.get('no_save_prev'):
            vals['arch_prev'] = self.arch_db

        res = super(View, self).write(self._compute_defaults(vals))

        # Check the xml of the view if it gets re-activated.
        # Ideally, `active` shoud have been added to the `api.constrains` of `_check_xml`,
        # but the ORM writes and validates regular field (such as `active`) before inverse fields (such as `arch`),
        # and therefore when writing `active` and `arch` at the same time, `_check_xml` is called twice,
        # and the first time it tries to validate the view without the modification to the arch,
        # which is problematic if the user corrects the view at the same time he re-enables it.
        if vals.get('active'):
            # Call `_validate_fields` instead of `_check_xml` to have the regular constrains error dialog
            # instead of the traceback dialog.
            self._validate_fields(['arch_db'])

        return res

    def unlink(self):
        # if in uninstall mode and has children views, emulate an ondelete cascade
        if self.env.context.get('_force_unlink', False) and self.inherit_children_ids:
            self.inherit_children_ids.unlink()
        return super(View, self).unlink()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        if self.key and default and 'key' not in default:
            new_key = self.key + '_%s' % str(uuid.uuid4())[:6]
            default = dict(default or {}, key=new_key)
        return super(View, self).copy(default)

    # default view selection
    @api.model
    def default_view(self, model, view_type):
        """ Fetches the default view for the provided (model, view_type) pair:
         primary view with the lowest priority.

        :param str model:
        :param int view_type:
        :return: id of the default view of False if none found
        :rtype: int
        """
        domain = [('model', '=', model), ('type', '=', view_type), ('mode', '=', 'primary')]
        return self.search(domain, limit=1).id

    #------------------------------------------------------
    # Inheritance mecanism
    #------------------------------------------------------
    @api.model
    def _get_inheriting_views_domain(self):
        """ Return a domain to filter the sub-views to inherit from. """
        return [('active', '=', True)]

    @api.model
    def _get_filter_xmlid_query(self):
        """This method is meant to be overridden by other modules.
        """
        return """SELECT res_id FROM ir_model_data
                  WHERE res_id IN %(res_ids)s AND model = 'ir.ui.view' AND module IN %(modules)s
               """

    def get_inheriting_views_arch(self, ids):
        """Retrieves the sets of views that should currently be used in the
           system in the right order. During the module upgrade phase it
           may happen that a view is present in the database but the fields it relies on are not
           fully loaded yet. This method only considers views that belong to modules whose code
           is already loaded. Custom views defined directly in the database are loaded only
           after the module initialization phase is completely finished.

           :param str model: model identifier of the inheriting views.
           :return: list of ir.ui.view
        """
        # retrieve all the views transitively inheriting from view_id
        self.flush(['active'])

        domain = self._get_inheriting_views_domain()
        e = expression(domain, self.env['ir.ui.view'])
        from_clause, where_clause, where_params = e.query.get_sql()

        query = """
WITH RECURSIVE ir_ui_view_inherits AS (
    SELECT id, inherit_id, priority, model
    FROM ir_ui_view
    WHERE id in %s AND {where_clause}
UNION
    SELECT iuv.id, iuv.inherit_id, iuv.priority, iuv.model
    FROM ir_ui_view iuv
    INNER JOIN ir_ui_view_inherits iuvi ON iuvi.id = iuv.inherit_id
    WHERE coalesce(iuv.model, '')=coalesce(iuvi.model, '') AND mode='extension' AND {sub_where_clause}
)
SELECT
    v.id, v.inherit_id,
    ARRAY(SELECT r.group_id FROM ir_ui_view_group_rel r WHERE r.view_id=v.id)
FROM ir_ui_view_inherits v
ORDER BY v.priority, v.id
""".format(where_clause=where_clause, sub_where_clause=where_clause.replace('ir_ui_view', 'iuv'))
        self.env.cr.execute(query, [tuple(ids)] + where_params + where_params)
        results = self.env.cr.fetchall()
        user_groups = set(self.env.user.groups_id.ids)
        results = list(filter(lambda x: not x[2] or (set(x[2]) & user_groups), results))

        views = {}
        view_ids = {r[0]: [] for r in results}
        for r in results:
            if r[1]:
                view_ids[r[1]].append(r[0])

        if self.pool._init and not self._context.get('load_all_views'):
            # check that all found ids have a corresponding xml_id in a loaded module
            check_view_ids = self._context.get('check_view_ids') or []
            ids_to_check = [vid for vid in view_ids if vid not in check_view_ids]
            if ids_to_check:
                loaded_modules = tuple(self.pool._init_modules) + (self._context.get('install_module'),)
                query = self._get_filter_xmlid_query()
                self.env.cr.execute(query, {'res_ids': tuple(ids_to_check), 'modules': loaded_modules})
                valid_view_ids = [r[0] for r in self.env.cr.fetchall()] + check_view_ids
                for key in list(view_ids.keys()):
                    if key not in valid_view_ids:
                        if key not in ids:
                            del view_ids[key]

        return view_ids

    def _check_view_access(self):
        """ Verify that a view is accessible by the current user based on the
        groups attribute. Views with no groups are considered private.
        """
        if self.inherit_id and self.mode != 'primary':
            return self.inherit_id._check_view_access()
        if self.groups_id & self.env.user.groups_id:
            return True
        if self.groups_id:
            error = _(
                "View '%(name)s' accessible only to groups %(groups)s ",
                name=self.key,
                groups=", ".join([g.name for g in self.groups_id]
            ))
        else:
            error = _("View '%(name)s' is private", name=self.key)
        raise AccessError(error)

    def _raise_view_error(self, message, node=None):
        """ Handle a view error by raising an exception.

        :param str message: message to raise or log, augmented with contextual
                            view information
        :param node: the lxml element where the error is located (if any)
        :param BaseException from_exception:
            when raising an exception, chain it to the provided one (default:
            disable chaining)
        :param types.TracebackType from_traceback:
            when raising an exception, start with this traceback (default: start
            at exception creation)
        """
        err = ValidationError(message)
        err.context = {
            'view': self,
            'name': getattr(self, 'name', None),
            'xmlid': self.env.context.get('install_xmlid') or self.xml_id,
            'view.model': self.model,
            'view.parent': self.inherit_id,
            'file': self.env.context.get('install_filename'),
            'line': node.sourceline if node is not None else 1,
        }
        raise err

    def _log_view_warning(self, message, node):
        """ Handle a view issue by logging a warning.

        :param str message: message to raise or log, augmented with contextual
                            view information
        :param node: the lxml element where the error is located (if any)
        """
        error_context = {
            'view': self,
            'name': getattr(self, 'name', None),
            'xmlid': self.env.context.get('install_xmlid') or self.xml_id,
            'view.model': self.model,
            'view.parent': self.inherit_id,
            'file': self.env.context.get('install_filename'),
            'line': node.sourceline if node is not None else 1,
        }
        _logger.warning(
            "%s\nView error context:\n%s",
            message, pprint.pformat(error_context)
        )


    def locate_node(self, arch, spec):
        """ Locate a node in a source (parent) architecture.

        Given a complete source (parent) architecture (i.e. the field
        `arch` in a view), and a 'spec' node (a node in an inheriting
        view that specifies the location in the source view of what
        should be changed), return (if it exists) the node in the
        source view matching the specification.

        :param arch: a parent architecture to modify
        :param spec: a modifying node in an inheriting view
        :return: a node in the source matching the spec
        """
        return locate_node(arch, spec)

    def inherit_branding(self, node):
        xpath = node.getroottree().getpath(node)
        if node.tag == 'data' or node.tag == 'xpath' or node.get('position'):
            for child in node.iterchildren(tag=etree.Element):
                self.inherit_branding(child)
        elif node.get('t-field'):
            node.set('data-oe-xpath', xpath)
            for child in node.iterchildren(tag=etree.Element):
                self.inherit_branding(child)
        else:
            node.set('data-oe-id', str(self.id))
            node.set('data-oe-xpath', xpath)
            node.set('data-oe-model', 'ir.ui.view')
            node.set('data-oe-field', 'arch')
        return node

    def _add_validation_flag(self, combined_arch, view=None, arch=None):
        """ Add a validation flag on elements in ``combined_arch`` or ``arch``.
        This is part of the partial validation of views.

        :param Element combined_arch: the architecture to be modified by ``arch``
        :param view: an optional view inheriting ``self``
        :param Element arch: an optional modifying architecture from inheriting
            view ``view``
        """
        # validate_view_ids is either falsy (no validation), True (full
        # validation) or a collection of ids (partial validation)
        validate_view_ids = self.env.context.get('validate_view_ids')
        if not validate_view_ids:
            return

        if validate_view_ids is True or self.id in validate_view_ids:
            # optimization, flag the root node
            combined_arch.set('__validate__', '1')
            return

        if view is None or view.id not in validate_view_ids:
            return

        for node in arch.xpath('//*[@position]'):
            if node.get('position') in ('after', 'before', 'inside'):
                # validate the elements being inserted, except the ones that
                # specify a move, as in:
                #   <field name="foo" position="after">
                #       <field name="bar" position="move"/>
                #   </field>
                for child in node.iterchildren(tag=etree.Element):
                    if not child.get('position'):
                        child.set('__validate__', '1')
            if node.get('position') == 'replace':
                # validate everything, since this impacts the whole arch
                combined_arch.set('__validate__', '1')
                break
            if node.get('position') == 'attributes':
                # validate the element being modified by adding
                # attribute "__validate__" on it:
                #   <field name="foo" position="attributes">
                #       <attribute name="readonly">1</attribute>
                #       <attribute name="__validate__">1</attribute>    <!-- add this -->
                #   </field>
                node.append(E.attribute('1', name='__validate__'))

    @api.model
    def apply_inheritance_specs(self, source, specs_tree, pre_locate=lambda s: True):
        """ Apply an inheriting view (a descendant of the base view)

        Apply to a source architecture all the spec nodes (i.e. nodes
        describing where and what changes to apply to some parent
        architecture) given by an inheriting view.

        :param Element source: a parent architecture to modify
        :param Element specs_tree: a modifying architecture in an inheriting view
        :param (optional) pre_locate: function that is execute before locating a node.
                                        This function receives an arch as argument.
        :return: a modified source where the specs are applied
        :rtype: Element
        """
        # Queue of specification nodes (i.e. nodes describing where and
        # changes to apply to some parent architecture).
        try:
            source = apply_inheritance_specs(
                source, specs_tree,
                inherit_branding=self._context.get('inherit_branding'),
                pre_locate=pre_locate,
            )
        except ValueError as e:
            self._raise_view_error(str(e), specs_tree)
        return source

    def _get_node(self, views, nodes={}):
        node = nodes.get(self.id, etree.fromstring(self.arch))
        if self._context.get('inherit_branding'):
            self.inherit_branding(node)

        for view in self.browse(views[self.id]):
            node2 = view._get_node(views, nodes)
            node = apply_inheritance_specs(node, node2, inherit_branding=self._context.get('inherit_branding'))
        return node

    def _get_arch(self):
        """
        Utility function to get a view combined with its inherited views, returns an etree node.
        """
        ids = []
        node = self
        root = self
        while node:
            ids.append(node.id)
            if node.mode == 'primary':
                root = node
            node = node.inherit_id

        # prefetch for performance
        views = root.get_inheriting_views_arch(ids)

        # useful to prefetch
        self.browse(views.keys()).mapped('arch_db')
        node = self.browse(root.id)._get_node(views)

        return node

    def get_arch(self):
        """
        Utility function to get a view combined with its inherited views, returns a string.
        """
        return etree.tostring(self._get_arch(), encoding="unicode")


    def _apply_groups(self, node, name_manager, node_info):
        #pylint: disable=unused-argument
        """ Apply group restrictions: elements with a 'groups' attribute should
        be made invisible to people who are not members.
        """
        if node.get('groups'):
            can_see = self.user_has_groups(groups=node.get('groups'))
            if not can_see:
                node.set('invisible', '1')
                node_info['modifiers']['invisible'] = True
                if 'attrs' in node.attrib:
                    del node.attrib['attrs']    # avoid making field visible later
            del node.attrib['groups']

    #------------------------------------------------------
    # Postprocessing: translation, groups and modifiers
    #------------------------------------------------------

    @api.model
    def _view_process(self, model, node):
        field_nodes = collections.defaultdict(list)
        fields = {}

        def _tag_form(model, node):
            title = model.view_header_get(False, 'form')
            if title:
                node.set('string', title)

        def _tag_calendar(model, node):
            for additional_field in ('date_start', 'date_delay', 'date_stop', 'color', 'all_day'):
                if node.get(additional_field):
                    fieldname = node.get(additional_field).split('.', 1)[0]
                    fields[fieldname] = {}
                    field = model._fields.get(fieldname)
                    field_nodes[field].append(node)

        def _tag_tree(model, node):
            title = model.view_header_get(False, 'form')
            if title:
                node.set('string', title)

        def _tag_label(model, node):
            field = model._fields.get(node.get('for'))
            if field and field.groups and not self.user_has_groups(groups=field.groups):
                node.getparent().remove(node)

        def _tag_filter(model, node):
            attrs = {key: node.get(key) for key in ('id', 'select') if node.get(key)}
            fields[node.get('name')] = attrs
            field = model._fields.get(node.get('name'))
            field_nodes[field].append(node)

        def _tag_groupby(model, node):
            # groupby nodes should be considered as nested view because they may
            # contain fields on the comodel
            field = model._fields.get(node.get('name'))
            if not field or not field.comodel_name:
                return
            # move all children nodes into a new node <groupby>
            groupby_node = E.groupby()
            for child in node:
                groupby_node.append(child)

            fields[node.get('name')] = {
                'fields': self._view_process(model, groupby_node),
                'arch': etree.tostring(groupby_node, encoding="unicode")
            }
            field_nodes[field].append(node)

        def _tag_field(model, node):
            attrs = {key: node.get(key) for key in ('id', 'select') if node.get(key)}
            fields[node.get('name')] = attrs
            field = model._fields.get(node.get('name'))

            # if the field does not exists on the object, but has been defined in
            # fields_get ovewrite: do nothing
            if not field:
                return

            field_nodes[field].append(node)

            # TODO: this is also tested by fields_get, optimization possible here?
            # if a group is set on a field, remove it from the view if user has no rights
            if field.groups and not self.user_has_groups(groups=field.groups):
                node.getparent().remove(node)
                return

            # TODO: cleanup API: remove fields.states and use modifiers only
            modifiers = {}
            transfer_field_to_modifiers(field, modifiers)

            # TODO: optimize: no need to "node2mod" & "mod2node" if field doesn't define the attribute)
            # uncomment the 'or True" by converting views modifiers into real JSON
            transfer_node_to_modifiers(node, modifiers, self._context)
            transfer_modifiers_to_node(modifiers, node)
            # TODO: check if we can uncomment this
            # del node.attrib['attrs']

            if field.comodel_name:
                model = self.env[field.comodel_name]

            # node_info['attr_model'] = comodel
            if field.type in ('many2one', 'many2many'):
                can_create = model.check_access_rights('create', raise_exception=False)
                can_write = model.check_access_rights('write', raise_exception=False)
                node.set('can_create', 'true' if can_create else 'false')
                node.set('can_write', 'true' if can_write else 'false')

            attrs['views'] = {}
            for child in node:
                if child.tag in ('form', 'tree', 'graph', 'kanban', 'calendar'):
                    node.remove(child)
                    attrs['views'][child.tag] = {
                        'fields': self._view_process(model, child),
                        'arch': etree.tostring(child, encoding="unicode")
                    }

        def _parse(model, node):
            tag = node.tag
            if node.get('groups'):
                if not self.user_has_groups(groups=node.get('groups')):
                    node.set('invisible', '1')
                    if 'attrs' in node.attrib:
                        del node.attrib['attrs']
                del node.attrib['groups']

            if tag == 'form':
                _tag_form(model, node)
            elif tag == 'tree':
                _tag_tree(model, node)

            # These tags handle the loop on children on their own
            if tag == 'label' and node.get('for'):
                _tag_label(model, node)
            elif tag == 'field' and node.get('name'):
                _tag_field(model, node)
            elif tag == 'groupby':
                _tag_field(model, node)
            else:
                for child in node:
                    _parse(model, child)

        _parse(model, node)

        # Apply on change on nodes referring to fields
        for field, nodes in field_nodes.items():
            model = self.env[field.model_name]
            if model._has_onchange(field, field_nodes):
                for node in nodes:
                    if not node.get('on_change'):
                        node.set('on_change', '1')

        fdata = fields and model.fields_get(fields.keys()) or []
        for f in fdata:
            fdata[f].update(fields[f])
        return fdata

    def _postprocess_access_rights(self, model, node):
        """ Compute and set on node access rights based on view type. Specific
        views can add additional specific rights like creating columns for
        many2one-based grouping views. """
        # testing ACL as real user
        is_base_model = self.env.context.get('base_model_name', model._name) == model._name

        if node.tag in ('kanban', 'tree', 'form', 'activity'):
            for action, operation in (('create', 'create'), ('delete', 'unlink'), ('edit', 'write')):
                if (not node.get(action) and
                        not model.check_access_rights(operation, raise_exception=False) or
                        not self._context.get(action, True) and is_base_model):
                    node.set(action, 'false')

        if node.tag == 'kanban':
            group_by_name = node.get('default_group_by')
            group_by_field = model._fields.get(group_by_name)
            if group_by_field and group_by_field.type == 'many2one':
                group_by_model = model.env[group_by_field.comodel_name]
                for action, operation in (('group_create', 'create'), ('group_delete', 'unlink'), ('group_edit', 'write')):
                    if (not node.get(action) and
                            not group_by_model.check_access_rights(operation, raise_exception=False) or
                            not self._context.get(action, True) and is_base_model):
                        node.set(action, 'false')

    def _check_tag_filter(self, node, models, fval):
        if node.attrib.get('domain'):
            expr = node.attrib.get('domain')
            fields = self._get_server_domain_variables(node, expr, 'domain of <%s%s> ' % (node.tag, (' name="%s"' % node.get('name')) if node.get('name') else '' ), models[-1])
            fval.has_fields(models, list(fields.keys()), node)

    def _check_tag_field(self, node, models, fval):
        model = models[-1]
        name = node.attrib.get('name')
        if not name:
            self._raise_view_error(_("Field tag must have a \"name\" attribute defined"), node)
        field = fval.field_get(model, name)
        if not field:
            msg = _(
                'Field "%(field_name)s" does not exist in model "%(model_name)s"',
                field_name=name, model_name=model._name,
            )
            self._raise_view_error(msg, node)
        if node.attrib.get('domain') and field.get('relation', None) not in self.env:
            msg = _(
                'Domain on non-relational field "%(name)s" makes no sense (domain:%(domain)s)',
                name=name, domain=node.get('domain'),
            )
            self._raise_view_error(msg, node)

        if node.attrib.get('domain'):
            model2 = self.env[field['relation']]
            expr = node.attrib.get('domain')
            fields = self._get_server_domain_variables(node, expr, 'domain of <%s%s> ' % (node.tag, (' name="%s"' % node.get('name')) if node.get('name') else '' ), model2)
            fval.has_fields(models, list(fields.keys()), node)
        elif field.get('relation'):
            fields = self._get_field_domain_variables(node, model._fields.get(name))
            fval.has_fields(models, list(fields.keys()), node)

        for attribute in ('invisible', 'readonly', 'required'):
            val = node.get(attribute)
            if val:
                res = safe_eval.safe_eval(val, {'context': self._context})
                if res not in (1, 0, True, False, None):
                    msg = _(
                        'Attribute %(attribute)s evaluation expects a boolean, got %(value)s',
                        attribute=attribute, value=val,
                    )
                    self._raise_view_error(msg, node)

    def _check_tag_button(self, node, models, fval):
        model = models[-1]
        name = node.get('name')
        special = node.get('special')
        type_ = node.get('type')
        if special:
            if special not in ('cancel', 'save', 'add'):
                self._raise_view_error(_("Invalid special '%(value)s' in button", value=special), node)
        elif type_:
            if type_ == 'edit': # list_renderer, used in kanban view
                return
            elif not name:
                self._raise_view_error(_("Button must have a name"), node)
            elif type_ == 'object':
                func = getattr(type(model), name, None)
                if not func:
                    msg = _(
                        "%(action_name)s is not a valid action on %(model_name)s",
                        action_name=name, model_name=model._name,
                    )
                    self._raise_view_error(msg, node)
                try:
                    check_method_name(name)
                except AccessError:
                    msg = _(
                        "%(method)s on %(model)s is private and cannot be called from a button",
                        method=name, model=model._name,
                    )
                    self._raise_view_error(msg, node)
                try:
                    inspect.signature(func).bind(self=model)
                except TypeError:
                    msg = "%s on %s has parameters and cannot be called from a button"
                    self._raise_view_error(msg % (name, model._name), node)
                fval.buttons.append(name)
            elif type_ == 'action':
                # logic mimics /web/action/load behaviour
                action = False
                try:
                    action_id = int(name)
                except ValueError:
                    model, action_id = self.env['ir.model.data']._xmlid_to_res_model_res_id(name, raise_if_not_found=False)
                    if not action_id:
                        msg = _("Invalid xmlid %(xmlid)s for button of type action.", xmlid=name)
                        self._raise_view_error(msg, node)
                    if not issubclass(self.pool[model], self.pool['ir.actions.actions']):
                        msg = _(
                            "%(xmlid)s is of type %(xmlid_model)s, expected a subclass of ir.actions.actions",
                            xmlid=name, xmlid_model=model,
                        )
                        self._raise_view_error(msg, node)
                action = self.env['ir.actions.actions'].browse(action_id).exists()
                if not action:
                    msg = _(
                        "Action %(action_reference)s (id: %(action_id)s) does not exist for button of type action.",
                        action_reference=name, action_id=action_id,
                    )
                    self._raise_view_error(msg, node)

        elif node.get('icon'):
            description = 'A button with icon attribute (%s)' % node.get('icon')
            self._validate_fa_class_accessibility(node, description)

    def _check_tag_graph(self, node, models, fval):
        for child in node.iterchildren(tag=etree.Element):
            if child.tag != 'field' and not isinstance(child, etree._Comment):
                msg = _('A <graph> can only contains <field> nodes, found a <%s>', child.tag)
                self._raise_view_error(msg, child)

    def _check_tag_groupby(self, node, models, fval):
        # groupby nodes should be considered as nested view because they may
        # contain fields on the comodel
        name = node.get('name')
        if name:
            field = models[-1]._fields.get(name)
            if field:
                if field.type != 'many2one':
                    msg = _(
                        "Field '%(name)s' found in 'groupby' node can only be of type many2one, found %(type)s",
                        name=field.name, type=field.type,
                    )
                    self._raise_view_error(msg, node)
            else:
                msg = _(
                    "Field '%(field)s' found in 'groupby' node does not exist in model %(model)s",
                    field=name, model=models[-1]._name,
                )
                self._raise_view_error(msg, node)

    def _check_tag_tree(self, node, models, fval):
        allowed_tags = ('field', 'button', 'control', 'groupby', 'widget', 'header')
        for child in node.iterchildren(tag=etree.Element):
            if child.tag not in allowed_tags and not isinstance(child, etree._Comment):
                msg = _(
                    'Tree child can only have one of %(tags)s tag (not %(wrong_tag)s)',
                    tags=', '.join(allowed_tags), wrong_tag=child.tag,
                )
                self._raise_view_error(msg, child)

    def _check_tag_search(self, node, models, fval):
        if len(list(node.iterchildren('searchpanel'))) > 1:
            self._raise_view_error(_('Search tag can only contain one search panel'), node)
        if not list(node.iterdescendants(tag="field")):
            # the field of the search view may be within a group node, which is why we must check
            # for all descendants containing a node with a field tag, if this is not the case
            # then a search is not possible.
            self._raise_view_error('Search tag requires at least one field element', node=node)

    def _check_tag_searchpanel(self, node, models, fval):
        for child in node.iterchildren(tag=etree.Element):
            if child.get('domain') and child.get('select') != 'multi':
                msg = _('Searchpanel item with select multi cannot have a domain.')
                self._raise_view_error(msg, child)

    def _check_tag_label(self, node, models, fval):
        # replace return not arch.xpath('//label[not(@for) and not(descendant::input)]')
        for_ = node.get('for')
        if not for_:
            msg = _('Label tag must contain a "for". To match label style '
                    'without corresponding field or button, use \'class="o_form_label"\'.')
            self._raise_view_error(msg, node)
        if for_ in fval.buttons:
            return
        fval.has_fields(models, [for_], node)

    def _check_tag_page(self, node, models, fval):
        if node.getparent() is None or node.getparent().tag != 'notebook':
            self._raise_view_error(_('Page direct ancestor must be notebook'), node)

    def _check_tag_img(self, node, models, fval):
        if not any(node.get(alt) for alt in self._att_list('alt')):
            self._raise_view_error(
                '<img> tag must contain an alt attribute',
                node=node
            )

    def _check_tag_a(self, node, models, fval):
        if any('btn' in node.get(cl, '') for cl in self._att_list('class')):
            if node.get('role') != 'button':
                msg = '"<a>" tag with "btn" class must have "button" role'
                self._log_view_warning(msg, node)

    def _check_tag_ul(self, node, models, fval):
        self._check_dropdown_menu(node)

    def _check_tag_div(self, node, models, fval):
        self._check_dropdown_menu(node)
        self._check_progress_bar(node)

    def _check_node(self, node, models, fval):
        tag = node.tag
        if type(tag) is not str:
            return
        if hasattr(self, '_check_tag_' + tag):
            getattr(self, '_check_tag_' + tag)(node, models, fval)

        self._validate_attrs(node, models, fval.has_fields)

        if node.tag in ('field', 'groupby'):
            name = node.attrib.get('name')
            field = models[-1]._fields.get(name)
            if field and field.comodel_name:
                models = models[:] + [ self.env[field.comodel_name] ]
        elif node.tag in ('searchpanel',):
            models = models[:] + [ models[-1] ]
        for child in node:
            self._check_node(child, models, fval)

    #------------------------------------------------------
    # Validation tools
    #------------------------------------------------------

    def _check_dropdown_menu(self, node):
        #('calendar', 'form', 'graph', 'kanban', 'pivot', 'search', 'tree', 'activity')
        if any('dropdown-menu' in node.get(cl, '') for cl in att_names('class')):
            if node.get('role') != 'menu':
                msg = 'dropdown-menu class must have menu role'
                self._log_view_warning(msg, node)

    def _check_progress_bar(self, node):
        if any('o_progressbar' in node.get(cl, '') for cl in att_names('class')):
            if node.get('role') != 'progressbar':
                msg = 'o_progressbar class must have progressbar role'
                self._log_view_warning(msg, node)
            if not any(node.get(at) for at in self._att_list('aria-valuenow')):
                msg = 'o_progressbar class must have aria-valuenow attribute'
                self._log_view_warning(msg, node)
            if not any(node.get(at) for at in self._att_list('aria-valuemin')):
                msg = 'o_progressbar class must have aria-valuemin attribute'
                self._log_view_warning(msg, node)
            if not any(node.get(at) for at in self._att_list('aria-valuemax')):
                msg = 'o_progressbar class must have aria-valuemaxattribute'
                self._log_view_warning(msg, node)

    def _att_list(self, name):
        return [name, 't-att-%s' % name, 't-attf-%s' % name]

    def _validate_attrs(self, node, models, has_fields):
        model = models[-1]
        """ Generic validation of node attrs. """
        for attr, expr in node.items():
            if attr.startswith('decoration-'):
                fields = dict.fromkeys(get_variable_names(expr), '%s=%s' % (attr, expr))
                has_fields(models, fields, node)

            elif attr == 'attrs':
                for key, val_ast in get_dict_asts(expr).items():
                    if isinstance(val_ast, ast.List):
                        # domains in attrs are used for readonly, invisible, ...
                        # and thus are only executed client side
                        fnames, vnames = self._get_domain_identifiers(node, val_ast, attr, expr)
                        has_fields(models, fnames, node)
                    else:
                        vnames = get_variable_names(val_ast)
                        has_fields(models, vnames, node)

            elif attr == 'context':
                for key, val_ast in get_dict_asts(expr).items():
                    if key == 'group_by':  # only in context
                        if not isinstance(val_ast, ast.Str):
                            msg = _(
                                '"group_by" value must be a string %(attribute)s=%(value)r',
                                attribute=attr, value=expr,
                            )
                            self._raise_view_error(msg, node)
                        group_by = val_ast.s
                        fname = group_by.split(':')[0]
                        if not fname in model._fields:
                            msg = _(
                                'Unknown field "%(field)s" in "group_by" value in %(attribute)s=%(value)r',
                                field=fname, attribute=attr, value=expr,
                            )
                            self._raise_view_error(msg, node)
                    else:
                        use = '%s.%s (%s)' % (attr, key, expr)
                        fields = dict.fromkeys(get_variable_names(val_ast), use)
                        has_fields(models, fields, node)

            elif attr in ('col', 'colspan'):
                # col check is mainly there for the tag 'group', but previous
                # check was generic in view form
                if not expr.isdigit():
                    self._raise_view_error(
                        _('%(attribute)r value must be an integer (%(value)s)', attribute=attr, value=expr),
                        node=node,
                    )

            elif attr in ('class', 't-att-class', 't-attf-class'):
                self._validate_classes(node, expr)

            elif attr == 'groups':
                # TODO: this seems very slow can we use another, cached method?
                for group in expr.replace('!', '').split(','):
                    try:
                        self.env['ir.model.data']._xmlid_lookup(group.strip())
                    except ValueError:
                        msg = "The group %r defined in view does not exist!"
                        self._log_view_warning(msg % group, node)

            elif attr == 'group':
                msg = "attribute 'group' is not valid.  Did you mean 'groups'?"
                self._raise_view_error(msg, node)

            elif attr == 'data-toggle' and expr == 'tab':
                if node.get('role') != 'tab':
                    msg = 'tab link (data-toggle="tab") must have "tab" role'
                    self._log_view_warning(msg, node)
                aria_control = node.get('aria-controls') or node.get('t-att-aria-controls')
                if not aria_control and not node.get('t-attf-aria-controls'):
                    msg = 'tab link (data-toggle="tab") must have "aria_control" defined'
                    self._log_view_warning(msg, node)
                if aria_control and '#' in aria_control:
                    msg = 'aria-controls in tablink cannot contains "#"'
                    self._log_view_warning(msg, node)

            elif attr == "role" and expr in ('presentation', 'none'):
                msg = ("A role cannot be `none` or `presentation`. "
                    "All your elements must be accessible with screen readers, describe it.")
                self._log_view_warning(msg, node)

            elif attr == 'group':
                msg = "attribute 'group' is not valid.  Did you mean 'groups'?"
                self._log_view_warning(msg, node)

    def _validate_classes(self, node, expr):
        """ Validate the classes present on node. """
        classes = set(expr.split(' '))
        # Be careful: not always true if it is an expression
        # example: <div t-attf-class="{{!selection_mode ? 'oe_kanban_color_' + kanban_getcolor(record.color.raw_value) : ''}} oe_kanban_card oe_kanban_global_click oe_applicant_kanban oe_semantic_html_override">
        if 'modal' in classes and node.get('role') != 'dialog':
            msg = '"modal" class should only be used with "dialog" role'
            self._log_view_warning(msg, node)

        if 'modal-header' in classes and node.tag != 'header':
            msg = '"modal-header" class should only be used in "header" tag'
            self._log_view_warning(msg, node)

        if 'modal-body' in classes and node.tag != 'main':
            msg = '"modal-body" class should only be used in "main" tag'
            self._log_view_warning(msg, node)

        if 'modal-footer' in classes and node.tag != 'footer':
            msg = '"modal-footer" class should only be used in "footer" tag'
            self._log_view_warning(msg, node)

        if 'tab-pane' in classes and node.get('role') != 'tabpanel':
            msg = '"tab-pane" class should only be used with "tabpanel" role'
            self._log_view_warning(msg, node)

        if 'nav-tabs' in classes and node.get('role') != 'tablist':
            msg = 'A tab list with class nav-tabs must have role="tablist"'
            self._log_view_warning(msg, node)

        if any(klass.startswith('alert-') for klass in classes):
            if (
                node.get('role') not in ('alert', 'alertdialog', 'status')
                and 'alert-link' not in classes
            ):
                msg = ("An alert (class alert-*) must have an alert, alertdialog or "
                        "status role or an alert-link class. Please use alert and "
                        "alertdialog only for what expects to stop any activity to "
                        "be read immediately.")
                self._log_view_warning(msg, node)

        if any(klass.startswith('fa-') for klass in classes):
            description = 'A <%s> with fa class (%s)' % (node.tag, expr)
            self._validate_fa_class_accessibility(node, description)

        if any(klass.startswith('btn') for klass in classes):
            if node.tag in ('a', 'button', 'select'):
                pass
            elif node.tag == 'input' and node.get('type') in ('button', 'submit', 'reset'):
                pass
            elif any(klass in classes for klass in ('btn-group', 'btn-toolbar', 'btn-ship')):
                pass
            else:
                msg = ("A simili button must be in tag a/button/select or tag `input` "
                        "with type button/submit/reset or have class in "
                        "btn-group/btn-toolbar/btn-ship")
                self._log_view_warning(msg, node)

    def _validate_fa_class_accessibility(self, node, description):
        valid_aria_attrs = {
            *att_names('title'), *att_names('aria-label'), *att_names('aria-labelledby'),
        }
        valid_t_attrs = {'t-value', 't-raw', 't-field', 't-esc', 't-out'}

        ## Following or preceding text
        if (node.tail or '').strip() or (node.getparent().text or '').strip():
            # text<i class="fa-..."/> or <i class="fa-..."/>text or
            return

        ## Following or preceding text in span
        def has_text(elem):
            if elem is None:
                return False
            if elem.tag == 'span' and elem.text:
                return True
            if elem.tag == 't' and (elem.get('t-esc') or elem.get('t-raw')):
                return True
            return False

        if has_text(node.getnext()) or has_text(node.getprevious()):
            return

        def has_title_or_aria_label(node):
            return any(node.get(attr) for attr in valid_aria_attrs)

        ## Aria label can be on ancestors
        if any(map(has_title_or_aria_label, node.iterancestors())):
            return

        if node.get('string'):
            return

        ## And we ignore all elements with describing in children
        def contains_description(node, depth=0):
            if depth > 2:
                _logger.warning('excessive depth in fa')
            if any(node.get(attr) for attr in valid_t_attrs):
                return True
            if has_title_or_aria_label(node):
                return True
            if node.tag in ('label', 'field'):
                return True
            if node.text:  # not sure, does it match *[text()]
                return True
            return any(contains_description(child, depth+1) for child in node)

        if contains_description(node):
            return

        msg = '%s must have title in its tag, parents, descendants or have text'
        self._log_view_warning(msg % description, node)

    def _get_domain_identifiers(self, node, domain, use, expr=None):
        try:
            return get_domain_identifiers(domain)
        except ValueError:
            msg = _("Invalid domain format %(expr)s in %(use)s", expr=expr or domain, use=use)
            self._raise_view_error(msg, node)

    def _get_server_domain_variables(self, node, domain, key, main_model):
        """ Returns all the variable names present in the given domain (to be
        used server-side).
        """
        try:
            (field_names, var_names) = get_domain_identifiers(domain)
        except ValueError:
            msg = _(
                'Invalid domain format: %(domain)s',
                domain=domain
            )
            self._raise_view_error(msg, node)

        # checking field names
        for name_seq in field_names:
            fnames = name_seq.split('.')
            try:
                model = main_model
                for fname in fnames:
                    if not isinstance(model, models.BaseModel):
                        msg = _(
                            'Trying to access "%(field)s" on %(model)s in path %(field_path)r in %(attribute)s=%(value)r',
                            field=fname, model=model, field_path=name_seq, attribute=key, value=domain,
                        )
                        self._raise_view_error(msg, node)
                    field = model._fields.get(fname)
                    if not field:
                        msg = _(
                            'Unknown field "%(model)s.%(field)s" in %(attribute)s %(value)r',
                            model=model._name, field=fname, attribute=key, value=domain,
                        )
                        self._raise_view_error(msg, node)
                    if not field._description_searchable:
                        msg = _(
                            'Unsearchable field "%(field)s" in path %(field_path)r in %(attribute)s=%(value)r',
                            field=field, field_path=name_seq, attribute=key, value=domain,
                        )
                        self._raise_view_error(msg, node)
                    model = self.env.get(field.comodel_name, None)
            except KeyError:
                msg = _(
                    'Unknown field "%(model)s.%(field)s" in %(attribute)s%(value)r',
                    model=model._name, field=fname, attribute=key, value=domain,
                )
                self._raise_view_error(msg, node)

        return dict.fromkeys(var_names, "%s (%s)" % (key, domain))

    def _get_field_domain_variables(self, node, field):
        """ Return the variable names present in the field's domain, if no
        domain is given on the node itself.
        """
        if node.get('readonly', False) in ("1", "True", "true"):
            return {}
        if field._description_readonly:
            return {}
        editable = False
        for parent in node.iterancestors('tree', 'form', 'graph', 'pivot', 'kanban', 'gantt', 'calendar'):
            if parent.tag=='form':
                editable = True
                for p2 in parent.iterancestors('field'):
                    if p2.attrib.get('readonly', False) in ("1", "True", "true"):
                        editable = False
            elif parent.tag=='tree':
                editable = parent.attrib.get('editable', False)
            break
        if editable and not node.get('domain'):
            domain = field._description_domain(self.env)
            if isinstance(domain, str):
                return self._get_server_domain_variables(
                    node,
                    domain,
                    'field %s default domain' % field.name,
                    self.env[field.comodel_name],
                )
        return {}

    #------------------------------------------------------
    # QWeb template views
    #------------------------------------------------------

    def _read_template_keys(self):
        """ Return the list of context keys to use for caching ``_read_template``. """
        return ['lang', 'inherit_branding', 'editable', 'translatable', 'edit_translations']

    # apply ormcache_context decorator unless in dev mode...
    @api.model
    @tools.conditional(
        'xml' not in config['dev_mode'],
        tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'view_id',
                       'tuple(self._context.get(k) for k in self._read_template_keys())'),
    )
    def _read_template(self, view_id):
        node = self.browse(view_id)._get_arch()
        # TODO: why do we do that in postprocessing?
        # TODO: speed improvement: if no distribute branding, we should not reparse the whole tree
        self.distribute_branding(node)
        arch = etree.tostring(node, encoding='unicode')
        return arch

    @api.model
    def get_view_id(self, template):
        """ Return the view ID corresponding to ``template``, which may be a
        view ID or an XML ID. Note that this method may be overridden for other
        kinds of template values.

        This method could return the ID of something that is not a view (when
        using fallback to `_xmlid_to_res_id`).
        """
        if isinstance(template, int):
            return template
        if '.' not in template:
            raise ValueError('Invalid template id: %r' % template)
        view = self.sudo().search([('key', '=', template)], limit=1)
        return view and view.id or self.env['ir.model.data']._xmlid_to_res_id(template, raise_if_not_found=True)

    def clear_cache(self):
        """ Deprecated, use `clear_caches` instead. """
        if 'xml' not in config['dev_mode']:
            self.clear_caches()

    def _contains_branded(self, node):
        return node.tag == 't'\
            or 't-raw' in node.attrib\
            or 't-call' in node.attrib\
            or any(self.is_node_branded(child) for child in node.iterdescendants())

    def _pop_view_branding(self, element):
        distributed_branding = dict(
            (attribute, element.attrib.pop(attribute))
            for attribute in MOVABLE_BRANDING
            if element.get(attribute))
        return distributed_branding

    def distribute_branding(self, e, branding=None, parent_xpath='',
                            index_map=ConstantMapping(1)):
        if e.get('t-ignore') or e.tag == 'head':
            # remove any view branding possibly injected by inheritance
            attrs = set(MOVABLE_BRANDING)
            for descendant in e.iterdescendants(tag=etree.Element):
                if not attrs.intersection(descendant.attrib):
                    continue
                self._pop_view_branding(descendant)
            # TODO: find a better name and check if we have a string to boolean helper
            return

        node_path = e.get('data-oe-xpath')
        if node_path is None:
            node_path = "%s/%s[%d]" % (parent_xpath, e.tag, index_map[e.tag])
        if branding:
            if e.get('t-field'):
                e.set('data-oe-xpath', node_path)
            elif not e.get('data-oe-model'):
                e.attrib.update(branding)
                e.set('data-oe-xpath', node_path)
        if not e.get('data-oe-model'):
            return

        if {'t-esc', 't-raw', 't-out'}.intersection(e.attrib):
            # nodes which fully generate their content and have no reason to
            # be branded because they can not sensibly be edited
            self._pop_view_branding(e)
        elif self._contains_branded(e):
            # if a branded element contains branded elements distribute own
            # branding to children unless it's t-raw, then just remove branding
            # on current element
            distributed_branding = self._pop_view_branding(e)

            if 't-raw' not in e.attrib:
                # TODO: collections.Counter if remove p2.6 compat
                # running index by tag type, for XPath query generation
                indexes = collections.defaultdict(lambda: 0)
                for child in e.iterchildren(tag=etree.Element):
                    if child.get('data-oe-xpath'):
                        # injected by view inheritance, skip otherwise
                        # generated xpath is incorrect
                        # Also, if a node is known to have been replaced during applying xpath
                        # increment its index to compute an accurate xpath for susequent nodes
                        replaced_node_tag = child.attrib.pop('meta-oe-xpath-replacing', None)
                        if replaced_node_tag:
                            indexes[replaced_node_tag] += 1
                        self.distribute_branding(child)
                    else:
                        indexes[child.tag] += 1
                        self.distribute_branding(
                            child, distributed_branding,
                            parent_xpath=node_path, index_map=indexes)

    def is_node_branded(self, node):
        """ Finds out whether a node is branded or qweb-active (bears a
        @data-oe-model or a @t-* *which is not t-field* as t-field does not
        section out views)

        :param node: an etree-compatible element to test
        :type node: etree._Element
        :rtype: boolean
        """
        return any(
            (attr in ('data-oe-model', 'groups') or (attr.startswith('t-')))
            for attr in node.attrib
        )

    @tools.ormcache('self.id')
    def get_view_xmlid(self):
        domain = [('model', '=', 'ir.ui.view'), ('res_id', '=', self.id)]
        xmlid = self.env['ir.model.data'].sudo().search_read(domain, ['module', 'name'])[0]
        return '%s.%s' % (xmlid['module'], xmlid['name'])

    @api.model
    def render_public_asset(self, template, values=None):
        template = self.sudo().browse(self.get_view_id(template))
        template._check_view_access()
        return template.sudo()._render(values, engine="ir.qweb")

    def _render_template(self, template, values=None, engine='ir.qweb'):
        return self.browse(self.get_view_id(template))._render(values, engine)

    def _render(self, values=None, engine='ir.qweb', minimal_qcontext=False):
        assert isinstance(self.id, int)

        qcontext = dict() if minimal_qcontext else self._prepare_qcontext()
        qcontext.update(values or {})

        return self.env[engine]._render(self.id, qcontext)

    @api.model
    def _prepare_qcontext(self):
        """ Returns the qcontext : rendering context with website specific value (required
            to render website layout template)
        """
        qcontext = dict(
            env=self.env,
            user_id=self.env["res.users"].browse(self.env.user.id),
            res_company=self.env.company.sudo(),
            keep_query=keep_query,
            request=request,  # might be unbound if we're not in an httprequest context
            debug=request.session.debug if request else '',
            test_mode_enabled=bool(config['test_enable'] or config['test_file']),
            json=json_scriptsafe,
            quote_plus=werkzeug.urls.url_quote_plus,
            time=safe_eval.time,
            datetime=safe_eval.datetime,
            relativedelta=relativedelta,
            xmlid=self.sudo().key,
            viewid=self.id,
            to_text=pycompat.to_text,
            image_data_uri=image_data_uri,
            # specific 'math' functions to ease rounding in templates and lessen controller marshmalling
            floor=math.floor,
            ceil=math.ceil,
        )
        return qcontext

    #------------------------------------------------------
    # Misc
    #------------------------------------------------------

    def open_translations(self):
        """ Open a view for editing the translations of field 'arch_db'. """
        return self.env['ir.translation'].translate_fields('ir.ui.view', self.id, 'arch_db')

    @api.model
    def _validate_custom_views(self, model):
        """Validate architecture of custom views (= without xml id) for a given model.
            This method is called at the end of registry update.
        """
        query = """SELECT max(v.id)
                     FROM ir_ui_view v
                LEFT JOIN ir_model_data md ON (md.model = 'ir.ui.view' AND md.res_id = v.id)
                    WHERE md.module IN (SELECT name FROM ir_module_module) IS NOT TRUE
                      AND v.model = %s
                      AND v.active = true
                 GROUP BY coalesce(v.inherit_id, v.id)"""
        self._cr.execute(query, [model])

        rec = self.browse(it[0] for it in self._cr.fetchall())
        return rec.with_context({'load_all_views': True})._check_xml()

    @api.model
    def _validate_module_views(self, module):
        """ Validate the architecture of all the views of a given module that
            are impacted by view updates, but have not been checked yet.
        """
        assert self.pool._init

        # only validate the views that still exist...
        prefix = module + '.'
        prefix_len = len(prefix)
        names = tuple(
            xmlid[prefix_len:]
            for xmlid in self.pool.loaded_xmlids
            if xmlid.startswith(prefix)
        )
        if not names:
            return

        # retrieve the views with an XML id that has not been checked yet, i.e.,
        # the views with noupdate=True on their xml id
        query = """
            SELECT v.id
            FROM ir_ui_view v
            JOIN ir_model_data md ON (md.model = 'ir.ui.view' AND md.res_id = v.id)
            WHERE md.module = %s AND md.name IN %s AND md.noupdate
        """
        self._cr.execute(query, (module, names))
        views = self.browse([row[0] for row in self._cr.fetchall()])

        for view in views:
            view._check_xml()

    def _create_all_specific_views(self, processed_modules):
        """To be overriden and have specific view behaviour on create"""
        pass

    def _get_specific_views(self):
        """ Given a view, return a record set containing all the specific views
            for that view's key.
        """
        self.ensure_one()
        # Only qweb views have a specific conterpart
        if self.type != 'qweb':
            return self.env['ir.ui.view']
        # A specific view can have a xml_id if exported/imported but it will not be equals to it's key (only generic view will).
        return self.with_context(active_test=False).search([('key', '=', self.key)]).filtered(lambda r: not r.xml_id == r.key)

    def _load_records_write(self, values):
        """ During module update, when updating a generic view, we should also
            update its specific views (COW'd).
            Note that we will only update unmodified fields. That will mimic the
            noupdate behavior on views having an ir.model.data.
        """
        if self.type == 'qweb':
            for cow_view in self._get_specific_views():
                authorized_vals = {}
                for key in values:
                    if key != 'inherit_id' and cow_view[key] == self[key]:
                        authorized_vals[key] = values[key]
                # if inherit_id update, replicate change on cow view but
                # only if that cow view inherit_id wasn't manually changed
                inherit_id = values.get('inherit_id')
                if inherit_id and self.inherit_id.id != inherit_id and \
                   cow_view.inherit_id.key == self.inherit_id.key:
                    self._load_records_write_on_cow(cow_view, inherit_id, authorized_vals)
                else:
                    cow_view.with_context(no_cow=True).write(authorized_vals)
        super(View, self)._load_records_write(values)

    def _load_records_write_on_cow(self, cow_view, inherit_id, values):
        # for modules updated before `website`, we need to
        # store the change to replay later on cow views
        if not hasattr(self.pool, 'website_views_to_adapt'):
            self.pool.website_views_to_adapt = []
        self.pool.website_views_to_adapt.append((
            cow_view.id,
            inherit_id,
            values,
        ))


class ResetViewArchWizard(models.TransientModel):
    """ A wizard to compare and reset views architecture. """
    _name = "reset.view.arch.wizard"
    _description = "Reset View Architecture Wizard"

    view_id = fields.Many2one('ir.ui.view', string='View')
    view_name = fields.Char(related='view_id.name', string='View Name')
    has_diff = fields.Boolean(compute='_compute_arch_diff')
    arch_diff = fields.Html(string='Architecture Diff', readonly=True,
                            compute='_compute_arch_diff', sanitize_tags=False)
    reset_mode = fields.Selection([
        ('soft', 'Restore previous version (soft reset).'),
        ('hard', 'Reset to file version (hard reset).'),
        ('other_view', 'Reset to another view.')],
        string='Reset Mode', default='soft', required=True)
    compare_view_id = fields.Many2one('ir.ui.view', string='Compare To View')
    arch_to_compare = fields.Text('Arch To Compare To', compute='_compute_arch_diff')

    @api.model
    def default_get(self, fields):
        view_ids = (self._context.get('active_model') == 'ir.ui.view' and
                    self._context.get('active_ids') or [])
        if len(view_ids) > 2:
            raise ValidationError(_("Can't compare more than two views."))

        result = super().default_get(fields)
        result['view_id'] = view_ids and view_ids[0]
        if len(view_ids) == 2:
            result['reset_mode'] = 'other_view'
            result['compare_view_id'] = view_ids[1]
        return result

    @api.depends('reset_mode', 'view_id', 'compare_view_id')
    def _compute_arch_diff(self):
        """ Depending of `reset_mode`, return the differences between the
        current view arch and either its previous arch, its initial arch or
        another view arch.
        """
        def get_table_name(view_id):
            name = view_id.display_name
            if view_id.key or view_id.xml_id:
                span = '<span class="ml-1 font-weight-normal small">(%s)</span>'
                name += span % (view_id.key or view_id.xml_id)
            return name

        for view in self:
            diff_to = False
            diff_to_name = False
            if view.reset_mode == 'soft':
                diff_to = view.view_id.arch_prev
                diff_to_name = _("Previous Arch")
            elif view.reset_mode == 'other_view':
                diff_to = view.compare_view_id.with_context(lang=None).arch
                diff_to_name = get_table_name(view.compare_view_id)
            elif view.reset_mode == 'hard' and view.view_id.arch_fs:
                diff_to = view.view_id.with_context(read_arch_from_file=True, lang=None).arch
                diff_to_name = _("File Arch")

            view.arch_to_compare = diff_to

            if not diff_to:
                view.arch_diff = False
                view.has_diff = False
            else:
                view_arch = view.view_id.with_context(lang=None).arch
                view.arch_diff = get_diff(
                    (view_arch, get_table_name(view.view_id) if view.reset_mode == 'other_view' else _("Current Arch")),
                    (diff_to, diff_to_name),
                )
                view.has_diff = view_arch != diff_to

    def reset_view_button(self):
        self.ensure_one()
        if self.reset_mode == 'other_view':
            self.view_id.write({'arch_db': self.arch_to_compare})
        else:
            self.view_id.reset_arch(self.reset_mode)
        return {'type': 'ir.actions.act_window_close'}
