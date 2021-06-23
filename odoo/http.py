# -*- coding: utf-8 -*-
#----------------------------------------------------------
# Odoo HTTP layer
#----------------------------------------------------------
import ast
import base64
import collections
import contextlib
import datetime
import functools
import hashlib
import hmac
import inspect
import json
import logging
import mimetypes
import os
import pprint
import random
import re
import sys
import threading
import time
import traceback
import zlib

import babel.core
import psycopg2
import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.local
import werkzeug.routing
import werkzeug.security
import werkzeug.urls
import werkzeug.wrappers
import werkzeug.wsgi

# Optional psutil, not packaged on windows
try:
    import psutil
except ImportError:
    psutil = None

import odoo
from .modules.module import module_manifest
from .service.server import memory_info
from .service import security, model as service_model
from .tools import ustr, consteq, frozendict, pycompat, unique, date_utils, DotDict
from .tools.mimetypes import guess_mimetype

#----------------------------------------------------------
# Logging
#----------------------------------------------------------

_logger = logging.getLogger(__name__)
_logger_rpc_request = logging.getLogger(__name__ + '.rpc.request')
_logger_rpc_response = logging.getLogger(__name__ + '.rpc.response')
_logger_rpc_request_flag = _logger_rpc_request.isEnabledFor(logging.DEBUG)
_logger_rpc_response_flag = _logger_rpc_response.isEnabledFor(logging.DEBUG) # should rather be named rpc content

#----------------------------------------------------------
# Lib fixes
#----------------------------------------------------------

# Add potentially missing (older ubuntu) font mime types
mimetypes.add_type('application/font-woff', '.woff')
mimetypes.add_type('application/vnd.ms-fontobject', '.eot')
mimetypes.add_type('application/x-font-ttf', '.ttf')
# Add potentially wrong (detected on windows) svg mime types
mimetypes.add_type('image/svg+xml', '.svg')

# To remove when corrected in Babel
babel.core.LOCALE_ALIASES['nb'] = 'nb_NO'

#----------------------------------------------------------
# Const
#----------------------------------------------------------

# Cache for static content from the filesystem is set to one week.
STATIC_CACHE = 3600 * 24 * 7

# Cache for content where the url uniquely identify the content (usually using
# a hash) may use what google page speed recommends (1 year)
STATIC_CACHE_LONG = 3600 * 24 * 365

""" Debug mode is stored in session and should always be a string.
    It can be activated with an URL query string `debug=<mode>` where
    mode is either:
    - 'tests' to load tests assets
    - 'assets' to load assets non minified
    - any other truthy value to enable simple debug mode (to show some
      technical feature, to show complete traceback in frontend error..)
    - any falsy value to disable debug mode

    You can use any truthy/falsy value from `str2bool` (eg: 'on', 'f'..)
    Multiple debug modes can be activated simultaneously, separated with
    a comma (eg: 'tests, assets').
"""
ALLOWED_DEBUG_MODES = ['', '1', 'assets', 'tests']

# don't trigger debugger for those exceptions, they carry user-facing warnings
# and indications, they're not necessarily indicative of anything being
# *broken*
NO_POSTMORTEM = (
    odoo.exceptions.except_orm,
    odoo.exceptions.AccessDenied,
    odoo.exceptions.Warning,
    odoo.exceptions.RedirectWarning,
)

MAX_TRIES_ON_CONCURRENCY_FAILURE = 5
PG_CONCURRENCY_ERRORS_TO_RETRY = {
    errorcodes.LOCK_NOT_AVAILABLE,
    errorcodes.SERIALIZATION_FAILURE,
    errorcodes.DEADLOCK_DETECTED,
}
NOT_NULL_VIOLATION_MESSAGE = """\
The operation cannot be completed:
- Create/update: a mandatory field is not set.
- Delete: another model requires the record being deleted. If possible, archive it instead.

Model: %(model_name)s (%(model_tech_name)s)
Field: %(field_name)s (%(field_tech_name)s)
"""
FOREIGN_KEY_VIOLATION_MESSAGE = """\
The operation cannot be completed: another model requires the record being deleted. If possible, archive it instead.

Model: %(model_name)s (%(model_tech_name)s)
Constraint: %(constraint)s
"""
CONSTRAINT_VIOLATION_MESSAGE = "The operation cannot be completed: %s"
INTEGRITY_ERROR_MESSAGE = "The operation cannot be completed: %s"

#----------------------------------------------------------
# Helpers
#----------------------------------------------------------
# Move to Request.json_exception
def serialize_exception(e):
    tmp = {
        "name": type(e).__module__ + "." + type(e).__name__ if type(e).__module__ else type(e).__name__,
        "debug": traceback.format_exc(),
        "message": ustr(e),
        "arguments": e.args,
        "exception_type": "internal_error",
        "context": getattr(e, 'context', {}),
    }
    if isinstance(e, odoo.exceptions.UserError):
        tmp["exception_type"] = "user_error"
    elif isinstance(e, odoo.exceptions.Warning):
        tmp["exception_type"] = "warning"
    elif isinstance(e, odoo.exceptions.RedirectWarning):
        tmp["exception_type"] = "warning"
    elif isinstance(e, odoo.exceptions.AccessError):
        tmp["exception_type"] = "access_error"
    elif isinstance(e, odoo.exceptions.MissingError):
        tmp["exception_type"] = "missing_error"
    elif isinstance(e, odoo.exceptions.AccessDenied):
        tmp["exception_type"] = "access_denied"
    elif isinstance(e, odoo.exceptions.ValidationError):
        tmp["exception_type"] = "validation_error"
    elif isinstance(e, odoo.exceptions.except_orm):
        tmp["exception_type"] = "except_orm"
    return tmp

# TODO check usage and remove of move to request as helper
def content_disposition(filename):
    filename = odoo.tools.ustr(filename)
    escaped = werkzeug.urls.url_quote(filename, safe='')

    return "attachment; filename*=UTF-8''%s" % escaped

def set_header_field(headers, name, value):
    """ Return new headers based on `headers` but with `value` set for the
    header field `name`.

    :param headers: the existing headers
    :type headers: list of tuples (name, value)

    :param name: the header field name
    :type name: string

    :param value: the value to set for the `name` header
    :type value: string

    :return: the updated headers
    :rtype: list of tuples (name, value)
    """
    dictheaders = dict(headers)
    dictheaders[name] = value
    return list(dictheaders.items())

def set_safe_image_headers(headers, content):
    """Return new headers based on `headers` but with `Content-Length` and
    `Content-Type` set appropriately depending on the given `content` only if it
    is safe to do."""
    content_type = guess_mimetype(content)
    safe_types = ['image/jpeg', 'image/png', 'image/gif', 'image/x-icon']
    if content_type in safe_types:
        headers = set_header_field(headers, 'Content-Type', content_type)
    set_header_field(headers, 'Content-Length', len(content))
    return headers

#----------------------------------------------------------
# Controller and routes
#----------------------------------------------------------
addons_manifest = {} # TODO move as attribute of application
controllers = collections.defaultdict(list)

class ControllerType(type):
    def __init__(cls, name, bases, attrs):
        super(ControllerType, cls).__init__(name, bases, attrs)

        # store the controller in the controllers list
        name = "%s.%s" % (cls.__module__, cls.__name__)
        class_path = name.split(".")
        if class_path[:2] == ["odoo", "addons"]:
            module = class_path[2]
            controllers[module].append(cls)
            _logger.info('controller %r %r %r', module, name, bases)

Controller = ControllerType('Controller', (object,), {})

def route(route=None, **kw):
    """Decorator marking the decorated method as being a handler for requests.
    The method must be part of a subclass of ``Controller``.

    :param route: string or array. The route part that will determine which
                  http requests will match the decorated method. Can be a
                  single string or an array of strings. See werkzeug's routing
                  documentation for the format of route expression (
                  http://werkzeug.pocoo.org/docs/routing/ ).
    :param type: The type of request, can be ``'http'`` or ``'json'``.
    :param auth: The type of authentication method, can on of the following:

                 * ``user``: The user must be authenticated and the current request
                   will perform using the rights of the user.
                 * ``public``: The user may or may not be authenticated. If she isn't,
                   the current request will perform using the shared Public user.
                 * ``none``: The method is always active, even if there is no
                   database. Mainly used by the framework and authentication
                   modules. There request code will not have any facilities to
                   access the current user.

    :param methods: A sequence of http methods this route applies to. If not
                    specified, all methods are allowed.
    :param cors: The Access-Control-Allow-Origin cors directive value.
    :param bool csrf: Whether CSRF protection should be enabled for the route.
                      Defaults to ``True``. See :ref:`CSRF Protection
                      <csrf>` for more.
    :param bool readonly: Whether this route will be readonly (no write into db
        nor session). Defaults to ``False``.
    """
    routing = kw.copy()
    assert routing.get('type','http') in ("http", "json")
    def decorator(f):
        if route:
            if isinstance(route, list):
                routes = route
            else:
                routes = [route]
            routing['routes'] = routes
        f.routing = routing
        return f
    return decorator

def _generate_routing_rules(modules, nodb_only, converters=None):
    classes = []
    for module in modules:
        classes += controllers.get(module, [])
    # process the controllers in reverse order of override
    classes.sort(key=lambda c: len(c.__bases__), reverse=True)
    # ingore inner nodes of the of the controllers inheritance tree
    ignore = set()
    for cls in classes:
        o = cls()
        for name, method in inspect.getmembers(o, inspect.ismethod):
            fullname = "%s.%s.%s" % (cls.__module__, cls.__name__, name)
            if fullname not in ignore:
                routing = {'type':'http', 'auth':'user', 'methods':None, 'routes':None, 'readonly':False}

                # browse inner (non leaf) inheritance to collect routing and ignore
                bases = list(cls.__bases__)
                inner = set()
                for base in bases:
                    m = getattr(base, name, None)
                    if m:
                        inner.add("%s.%s.%s" % (base.__module__, base.__name__, name))
                    routing.update(getattr(m, 'routing', {}))

                routing.update(getattr(method, 'routing', {}))
                if routing['routes']:
                    ignore |= inner
                    if not nodb_only or routing['auth'] == "none":
                        for url in routing['routes']:
                            yield (url, method, routing)

#----------------------------------------------------------
# Request and Response
#----------------------------------------------------------
# Thread local global request object
_request_stack = werkzeug.local.LocalStack()
# global proxy that always redirect to the thread local request object.
request = _request_stack()

class Response(werkzeug.wrappers.Response):
    """ Response object passed through controller route chain.

    In addition to the :class:`werkzeug.wrappers.Response` parameters, this
    class's constructor can take the following additional parameters
    for QWeb Lazy Rendering.

    :param basestring template: template to render
    :param dict qcontext: Rendering context to use
    :param int uid: User id to use for the ir.ui.view render call,
                    ``None`` to use the request's user (the default)

    these attributes are available as parameters on the Response object and
    can be altered at any time before rendering

    Also exposes all the attributes and methods of
    :class:`werkzeug.wrappers.Response`.
    """
    default_mimetype = 'text/html'
    def __init__(self, *args, **kw):
        template = kw.pop('template', None)
        qcontext = kw.pop('qcontext', None)
        uid = kw.pop('uid', None)
        super(Response, self).__init__(*args, **kw)
        self.set_default(template, qcontext, uid)

    def set_default(self, template=None, qcontext=None, uid=None):
        # TODO is needed ?
        self.template = template
        _logger.info("reponse template %s",self.template)
        self.qcontext = qcontext or dict()
        self.qcontext['response_template'] = self.template
        self.uid = uid
        # TODO remove ? self.endpoint is needed because of this
        # Support for Cross-Origin Resource Sharing
        if request.endpoint and 'cors' in request.endpoint.routing:
            self.headers.set('Access-Control-Allow-Origin', request.endpoint.routing['cors'])
            methods = 'GET, POST'
            if request.endpoint.routing['type'] == 'json':
                methods = 'POST'
            elif request.endpoint.routing.get('methods'):
                methods = ', '.join(request.endpoint.routing['methods'])
            self.headers.set('Access-Control-Allow-Methods', methods)

    @property
    def is_qweb(self):
        _logger.info("reponse is qweb template %s",self.template)
        return self.template is not None

    def render(self):
        # WHY lazy qweb again ?
        """ Renders the Response's template, returns the result
        """
        self.qcontext['request'] = request
        # Should we support uid ?
        return request.env["ir.ui.view"]._render_template(self.template, self.qcontext)

    def flatten(self):
        """ Forces the rendering of the response's template, sets the result
        as response body and unsets :attr:`.template`
        """
        if self.template:
            self.response.append(self.render())
            self.template = None

    def update(self, *args, **kwargs):
        """Replace headers in this object with items from another headers object and keyword arguments.
        To extend existing keys instead of replacing, use :meth:`extend` instead.
        If provided, the first argument can be another :class:`Headers` object, a :class:`MultiDict`, :class:`dict`, or iterable of pairs.
        .. versionadded:: 1.0
        """
        if len(args) > 1:
            raise TypeError(f"update expected at most 1 arguments, got {len(args)}")

        if args:
            mapping = args[0]

class Request(object):
    """ Odoo request.

    :param httprequest: a wrapped werkzeug Request object
    :type httprequest: :class:`werkzeug.wrappers.BaseRequest`

    .. attribute:: httprequest

        the original :class:`werkzeug.wrappers.Request` object

    .. attribute:: params

        :class:`~collections.Mapping` of request parameters, also provided
        directly to the handler method as keyword arguments
    """
    def __init__(self, app, httprequest):
        self.app = app
        self.httprequest = httprequest
        self.params = None

        # Session
        self.session_sid = None
        self.session_mono = None
        self.session_orig = None
        self.session_rotate = None
        self.session = {}

        # Environment
        self.db = None
        self.cr = None
        self.env = None

        # TODO remove
        self.endpoint = None
        # prevents transaction commit, use when you catch an exception during handling
        self._failed = None
        # To check for REMOVAL: self.session_db = None self.auth_method = None self._request_type = None self._cr = None self._uid = None self._context = None self._env = None

        # Response
        # We keep a default one and then we merge headers._list #self.response_headers = werkzeug.datastructures.Headers()
        self.response = werkzeug.wrappers.Response(mimetype='text/html')
        self.response_template = None
        self.response_qcontext = None

    #------------------------------------------------------
    # Common helpers
    #------------------------------------------------------
    def send_file(self, content, filename=None, mimetype=None, mtime=None, as_attachment=False, cache_timeout=STATIC_CACHE):
        """Send file, str or bytes content with mime and cache handling.

        Sends the contents of a file to the client.  Using werkzeug file_wrapper
        support.

        If filename of content.name is provided it will try to guess the mimetype
        for you, but you can also explicitly provide one.

        :param content : fileobject to read from or str or bytes.
        :param filename: optional if content has a 'name' attribute, used for attachment name and mimetype guess (i.e. io.BytesIO)
        :param mimetype: the mimetype of the file if provided, otherwise auto detection happens based on the name.
        :param mtime: optional if content has a 'name' attribute, last modification time used for contitional response.
        :param as_attachment: set to `True` if you want to send this file with a ``Content-Disposition: attachment`` header.
        :param cache_timeout: set to `False` to disable etags and conditional response handling (last modified and etags)
        """

        # REM for odo i removed the unsafe path api
        if isinstance(content, str):
            content = content.encode('utf8')
        if isinstance(content, bytes):
            content = io.BytesIO(content)

        # Only used when filename or mtime argument is not provided
        path = getattr(content, 'name', 'file.bin')

        if not filename:
            filename = os.path.basename(path)

        if not mimetype:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        if not mtime:
            try:
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
            except Exception:
                pass

        content.seek(0, 2)
        size = content.tell()
        content.seek(0)

        data = werkzeug.wsgi.wrap_file(self.httprequest.environ, content)

        r = werkzeug.wrappers.Response(data, mimetype=mimetype, direct_passthrough=True)
        r.content_length = size

        if as_attachment:
            r.headers.add('Content-Disposition', 'attachment', filename=filename or 'file.bin')

        if cache_timeout:
            if mtime:
                r.last_modified = mtime
            crc = zlib.adler32(filename.encode('utf-8') if isinstance(filename, str) else filename) & 0xffffffff
            etag = 'odoo-%s-%s-%s' % ( mtime, size, crc)
            if not werkzeug.http.is_resource_modified(self.httprequest.environ, etag, last_modified=mtime):
                r = werkzeug.wrappers.Response(status=304)
            else:
                r.cache_control.public = True
                r.cache_control.max_age = cache_timeout
                # expires is deprecated
                #r.expires = int(time.time() + cache_timeout)
                r.set_etag(etag)
        _logger.info("response %s", r)
        return r

    def _setup_thread(self):
        # cleanup db/uid trackers - they're set in Request or in for
        # servie rpc in odoo.service.*.dispatch().
        # /!\ The cleanup cannot be done at the end of this `application`
        # method because werkzeug still produces relevant logging
        # afterwards


        current_thread = threading.current_thread()
        if hasattr(current_thread, 'uid'):
            del current_thread.uid
        if hasattr(current_thread, 'dbname'):
            del current_thread.dbname
        current_thread.url = self.httprequest.url
        current_thread.query_count = 0
        current_thread.query_time = 0
        current_thread.perf_t0 = time.time()

        # TODO db handling
        # set db/uid trackers - they're cleaned up at the WSGI
        # dispatching phase in odoo.http.application
        if self.db:
            threading.current_thread().dbname = self.db
        if self.session.uid:
            threading.current_thread().uid = self.session.uid

    def _call_function(self, endpoint, *args, **kwargs):
        def as_validation_error(exc):
            """ Return the IntegrityError encapsuled in a nice ValidationError """
            unknown = _('Unknown')
            for name, rclass in self.env.registry.items():
                if inst.diag.table_name == rclass._table:
                    model = rclass
                    field = model._fields.get(inst.diag.column_name)
                    break
            else:
                model = DotDict({'_name': unknown.lower(), '_description': unknown})
                field = DotDict({'name': unknown.lower(), 'string': unknown})

            if exc.code == NOT_NULL_VIOLATION:
                return ValidationError(_(NOT_NULL_VIOLATION_MESSAGE, **{
                    'model_name': model._description,
                    'model_tech_name': model._name,
                    'field_name': field.string,
                    'field_tech_name': field.name
                }))

            if exc.code == FOREIGN_KEY_VIOLATION:
                return ValidationError(_(FOREIGN_KEY_VIOLATION_MESSAGE, **{
                    'model_name': model._description,
                    'model_tech_name': model._name, 
                    'constraint': exc.diag.constraint_name,
                }))

            if exc.diag.constraint_name in registry._sql_constraints:
                return ValidationError(_(CONSTRAINT_VIOLATION_MESSAGE,
                    translate_sql_constraint(exc.diag.constraint_name, self.env.cr, self.env.context['lang'])
                ))

            return ValidationError(_(INTEGRITY_ERROR_MESSAGE, exc.args[0]))

        # Execute the business code. In case the SQL transaction failed due
        # to a serialization failure (like two transactions writing on a
        # same record) wait a bit and retry. Other exceptions bubble up.
        for tryno in range(1, MAX_TRIES_ON_CONCURRENCY_FAILURE + 1):
            try:
                result = endpoint(*args, **kwargs)
                if isinstance(result, Response) and result.is_qweb:
                    result.flatten()
                flush_env(self.env.cr)
                self.env.cr.precommit()
                self.env['base'].flush()
                return result
            except (IntegrityError, OperationalError) as exc:
                self.env.cr.rollback()  # cursor is wasted and must be reniewed before the next query
                self.env.clear()
                if type(exc) is IntegrityError:
                    raise as_validation_error(exc) from exc
                if e.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY:
                    raise

                # would ideally go outside of the for-loop but it is only
                # possible to re-raise from within an except block
                if tries == MAX_TRIES_ON_CONCURRENCY_FAILURE:
                    _logger.info("%s, was %s/%s, maximum number of tries reached!",
                        errorcodes.lookup(e.pgcode), tryno, MAX_TRIES_ON_CONCURRENCY_FAILURE)
                    raise

            wait_time = random.uniform(0.0, 2 ** tries)
            _logger.info("%s, was %s/%s, try again in %.04f sec...",
                errorcodes.lookup(e.pgcode), tryno, MAX_TRIES_ON_CONCURRENCY_FAILURE, wait_time)
            time.sleep(wait_time)

        raise RuntimeError("unreachable")

    def rpc_debug_pre(self, endpoint, params, model=None, method=None):
        # For Odoo service RPC params is a list or a tuple, for call_kw style it is a dict
        if _logger_rpc_request_flag or _logger_rpc_response_flag:
            name = endpoint.method.__name__
            model = model or params.get('model')
            method = method or params.get('method')

            # For Odoo service RPC call password is always 3rd argument in a
            # request, we replace it in logs so it's easier to forward logs for
            # diagnostics/debugging purposes...
            if isinstance(params, (tuple, list)):
                if len(params) > 2:
                    log_params = list(params)
                    log_params[2] = '*'

            start_time = time.time()
            start_memory = 0
            if psutil:
                start_memory = memory_info(psutil.Process(os.getpid()))
            _logger_rpc_request.debug('%s: request %s.%s: %s', name, model, method, pprint.pformat(params))
            return (name, model, method, start_time, start_memory)

    def rpc_debug_post(self, t0, result):
        if _logger_rpc_request_flag or _logger_rpc_response_flag:
            endpoint, model, method, start_time, start_memory = t0
            end_time = time.time()
            end_memory = 0
            if psutil:
                end_memory = memory_info(psutil.Process(os.getpid()))
            logline = '%s: response %s.%s: time:%.3fs mem: %sk -> %sk (diff: %sk)' % (name, model, method, end_time - start_time, start_memory / 1024, end_memory / 1024, (end_memory - start_memory)/1024)
            if _logger_rpc_response_flag:
                rpc_response.debug('%s, response: %s', logline, pprint.pformat(result))
            else:
                rpc_request.debug(logline)

    def rpc_service(self, service_name, method, args):
        """ Handle an Odoo Service RPC call.  """
        try:
            threading.current_thread().uid = None
            threading.current_thread().dbname = None

            t0 = self.rpc_debug_pre(args, service_name, method)

            result = False
            if service_name == 'common':
                result = odoo.service.common.dispatch(method, args)
            elif service_name == 'db':
                result = odoo.service.db.dispatch(method, args)
            elif service_name == 'object':
                result = odoo.service.model.dispatch(method, args)

            t0 = self.rpc_debug_post(t0, result)

            return result
        except NO_POSTMORTEM:
            raise
        except odoo.exceptions.DeferredException as e:
            _logger.exception(odoo.tools.exception_to_unicode(e))
            odoo.tools.debugger.post_mortem(odoo.tools.config, e.traceback)
            raise
        except Exception as e:
            _logger.exception(odoo.tools.exception_to_unicode(e))
            odoo.tools.debugger.post_mortem(odoo.tools.config, sys.exc_info())
            raise

    #------------------------------------------------------
    # Session
    #------------------------------------------------------
    def session_locate_db(self, cookie_dbname):
        """ Rationale
        For
        - easier to invalidate session (remove res.user cache crap)
        - moving of seamlessly db across server is now possible
        - easier deployement only filestore and db
        Against
        - select data from table where key = sid might be slower than open(),read()
        - dev mode need to store dbanme in cookie and one sql query more to list
        """
        if odoo.tools.config['db_name']:
            # Production mode --database defined as a comma seperated list of
            # exposed databases. Beware that existence is not guaranted.
            dbs = [db.strip() for db in odoo.tools.config['db_name'].split(',')]
        else:
            # Development mode where the list of all available dbs is checked
            # this generate one (potentially big) sql query for every request
            # TODO use cookie_dbname and regex to filter list in sql
            dbs = odoo.service.db.list_dbs(force)
            if odoo.tools.config['dbfilter']:
                host = self.httprequest.environ.get('HTTP_HOST', '').split(':')[0]
                domain, _, r = host.partition('.')
                if domain == "www" and r:
                    domain = r.partition('.')[0]
                domain, host = re.escape(d), re.escape(host)
                regex = odoo.tools.config['dbfilter'].replace('%h', host).replace('%d', domain)
                dbs = [i for i in re.match(regex, i)]

        if cookie_dbname in dbs:
            self.session_db = cookie_dbname
        else:
            if len(dbs):
                self.session_db = dbs[0]
            else:
                self.session_db = None
        self.session_mono = len(dbs) == 1
        return self.session_db

        #    def setup_db(self, httprequest):
        #        db = httprequest.session.db
        #        # Check if session.db is legit
        #        if db:
        #            if db not in db_filter([db], httprequest=httprequest):
        #                _logger.warning("Logged into database '%s', but dbfilter rejects it; logging session out.", db)
        #                httprequest.session.logout()
        #                db = None

    def session_reset_env(self):
        # No uid means 1, I know it looks dangerous but it's checked again in
        # ir.http dispatch auth_*
        uid = self.session["uid"] or 1
        # TODO load context
        self.env = odoo.api.Environment(self.cr, uid, {})

    def session_pre(self):


        # example 'Cookie: session_id=CR2SuuwwY7KEjIm2JpJFk2S0bHkdQP2INAViiTnV'
        # example 'Cookie: session_id=CR2SuuwwY7KEjIm2JpJFk2S0bHkdQP2INAViiTnV_mydb'
        "Set-Cookie: session_id=CR2SuuwwY7KEjIm2JpJFk2S0bHkdQP2INAViiTnV_mydb; Expires=Sat, 05-Jun-2021 22:04:27 GMT; Max-Age=7776000; HttpOnly; Path=/"

        cookie = self.httprequest.cookies.get('session_id','')
        cookie_dbname = None
        r = re.match('([0-9a-zA-Z]{40})(_([0-9a-zA-Z_-]{1,64}))?',cookie)
        if r:
            self.session_sid = r.group(1)
            cookie_dbname = r.group(3)

        # Decode session
        self.session_orig = "{}"
        self.session = {
            "uid": None,
            "login": None,
            "token": None, # TODO REMOVE
            "context": {},
            "debug": '',
        }

        #def setup_lang(self, httprequest):
        #    if "lang" not in httprequest.session.context:
        #        alang = httprequest.accept_languages.best or "en-US"
        #        try:
        #            code, territory, _, _ = babel.core.parse_locale(alang, sep='-')
        #            if territory:
        #                lang = '%s_%s' % (code, territory)
        #            else:
        #                lang = babel.core.LOCALE_ALIASES[code]
        #        except (ValueError, KeyError):
        #            lang = 'en_US'
        #        httprequest.session.context["lang"] = lang

        dbname = self.session_locate_db(cookie_dbname)
        if dbname:
            try:
                registry = odoo.registry(dbname)
                registry.check_signaling()
                self.cr = registry.cursor()
                self.cr.execute("SELECT json FROM ir_session WHERE sid = %s", (self.session_sid,))
                select = self.cr.fetchall()

            except (AttributeError, psycopg2.OperationalError, psycopg2.ProgrammingError) as e:
                # psycopg2 error or attribute error while constructing
                # the registry. That means either
                # - the database probably does not exists anymore
                # - the database is corrupted
                # - the database version doesnt match the server version
                raise e
                self.session_logout()
                return werkzeug.utils.redirect('/web/database/selector')

            self.db = dbname
            #self._setup_thread()
            #import pudb; pu.db
            if select:
                self.session_orig = select[0][0]
                self.session = json.loads(self.session_orig)

            self.session_reset_env()
            #raise 1

    # TODO move to ir.http
    def session_authenticate_start(self, login=None, password=None):
        """ Authenticate the current user with the given db, login and
        password. If successful, store the authentication parameters in the
        current session and request, unless multi-factor-authentication is
        activated. In that case, that last part will be done by
        :ref:`session_authenticate_finalize`.
        """
        wsgienv = {
            "interactive" : True,
            "base_location" : request.httprequest.url_root.rstrip('/'),
            "HTTP_HOST" : request.httprequest.environ['HTTP_HOST'],
            "REMOTE_ADDR" : request.httprequest.environ['REMOTE_ADDR'],
        }
        uid = self.env['res.users'].authenticate(self.db, login, password, wsgienv)
        _logger.info("UID %s",uid)

        self.session["session_authenticate_start_login"] = login
        self.session["session_authenticate_start_uid"] = uid
        #self.rotate = True

        # if 2FA is disabled we finalize immediatly
        user = self.env(user=uid)['res.users'].browse(uid)
        if not user._mfa_url():
            self.session_authenticate_finalize()

    def session_authenticate_finalize(self):
        """ Finalizes a partial session, should be called on MFA validation to
        convert a partial / pre-session into a full-fledged "logged-in" one """
        #self.rotate = True
        self.session["login"] = self.session.pop('session_authenticate_start_login')
        self.session["uid"] = self.session.pop('session_authenticate_start_uid')
        #self.env[]
        self.env = odoo.api.Environment(self.cr, self.session["uid"], {})

    def session_setup_context(self):
        user = self.env['res.users'].browse(self.session["uid"])
        context = user.context_get() or {}
        #        self.context['uid'] = self.uid
        #        self._fix_lang(self.context)
        #
        #    def _fix_lang(self, context):
        #        """ OpenERP provides languages which may not make sense and/or may not
        #        be understood by the web client's libraries.
        #
        #        Fix those here.
        #
        #        :param dict context: context to fix
        #        """
        #        lang = context.get('lang')
        #
        #        # inane OpenERP locale
        #        if lang == 'ar_AR':
        #            lang = 'ar'
        #
        #        # lang to lang_REGION (datejs only handles lang_REGION, no bare langs)
        #        if lang in babel.core.LOCALE_ALIASES:
        #            lang = babel.core.LOCALE_ALIASES[lang]
        #
        #        context['lang'] = lang or 'en_US'
        pass
        #    def logout(self, keep_db=False):
        #        for k in list(self):
        #            if not (keep_db and k == 'db') and k != 'debug':
        #                del self[k]
        #        self._default_values()
        #        self.rotate = True
        #

    def session_post(self):
        #    save_session = (not request.endpoint) or request.endpoint.routing.get('save_session', True)
        #    if not save_session:
        #        return

        #def session_gc(session_store): -> Move to daily CRON
        #    if random.random() < 0.001:
        #        # we keep session one week
        #        last_week = time.time() - 60*60*24*7
        #        for fname in os.listdir(session_store.path):
        #            path = os.path.join(session_store.path, fname)
        #            try:
        #                if os.path.getmtime(path) < last_week:
        #                    os.unlink(path)
        #            except OSError:
        #                pass
        # TODO delete, rotate

        if self.db:

            dump = json.dumps(self.session, ensure_ascii=False, separators=(',', ':'), sort_keys=True)

            _logger.info("old  %s new  %s ", self.session_orig , dump);

            if self.session_orig != dump:
                if not self.session_sid:
                    # 232 bits (30*8*62/64) of urandom entropy should be enough for everyone
                    self.session_sid = base64.b64encode(os.urandom(30)).decode('ascii').replace('/','a').replace('+','l')
                # SAVE in DB

                self.cr.execute("""
                    INSERT INTO ir_session (sid, create_date, write_date, json) VALUES (%s, NOW(), NOW(), %s)
                    ON CONFLICT (sid) DO UPDATE SET write_date = NOW(), json = %s
                """, (self.session_sid, dump, dump));

            # Set reply
            sid = self.session_sid
            if not self.session_mono:
                sid += "_" + self.session_db
            # cookie_samesite="Lax" ?  cookie_path="/" ?
            self.response.set_cookie('session_id', sid, max_age=90 * 24 * 60 * 60, httponly=True)

    #------------------------------------------------------
    # HTTP Controllers
    #------------------------------------------------------
    def redirect(self, path, query=None, code=303):
        url = path
        if not query:
            query = {}
        if query:
            url += '?' + werkzeug.urls.url_encode(query)
        return werkzeug.utils.redirect(url, code)

    def render(self, template, qcontext=None, lazy=True, **kw):
        """ Lazy render of a QWeb template.

        The actual rendering of the given template will occur at then end of
        the dispatching. Meanwhile, the template and/or qcontext can be
        altered or even replaced by a static response.

        :param basestring template: template to render
        :param dict qcontext: Rendering context to use
        :param bool lazy: whether the template rendering should be deferred
                          until the last possible moment
        :param kw: forwarded to werkzeug's Response object
        """
        response = Response(template=template, qcontext=qcontext, **kw)
        if not lazy:
            return response.render()
        return response

    def not_found(self, description=None):
        """ Shortcut for a `HTTP 404
        <http://tools.ietf.org/html/rfc7231#section-6.5.4>`_ (Not Found)
        response
        """
        return werkzeug.exceptions.NotFound(description)

    def make_response(self, data, headers=None, cookies=None):
        """ Helper for non-HTML responses, or HTML responses with custom
        response headers or cookies.

        While handlers can just return the HTML markup of a page they want to
        send as a string if non-HTML data is returned they need to create a
        complete response object, or the returned data will not be correctly
        interpreted by the clients.

        :param basestring data: response body
        :param headers: HTTP headers to set on the response
        :type headers: ``[(name, value)]``
        :param collections.Mapping cookies: cookies to set on the client
        """
        response = Response(data, headers=headers)
        if cookies:
            for k, v in cookies.items():
                response.set_cookie(k, v)
        return response

    def csrf_token(self, time_limit=3600*48):
        """ Generates and returns a CSRF token for the current session

        :param time_limit: the CSRF token should only be valid for the
                           specified duration (in second), by default 48h,
                           ``None`` for the token to be valid as long as the
                           current user's session is.
        :type time_limit: int | None
        :returns: ASCII token string
        """
        token = self.session_sid
        # if no `time_limit` => distant 1y expiry (31536000) so max_ts acts as salt, e.g. vs BREACH
        max_ts = int(time.time() + (time_limit or 31536000))

        msg = '%s%s' % (token, max_ts)
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        assert secret, "CSRF protection requires a configured database secret"
        hm = hmac.new(secret.encode('ascii'), msg.encode('utf-8'), hashlib.sha1).hexdigest()
        return '%so%s' % (hm, max_ts)

    def validate_csrf(self, csrf):
        if not csrf:
            return False

        try:
            hm, _, max_ts = str(csrf).rpartition('o')
        except UnicodeEncodeError:
            return False

        if max_ts:
            try:
                if int(max_ts) < int(time.time()):
                    return False
            except ValueError:
                return False

        token = self.session_sid

        msg = '%s%s' % (token, max_ts)
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        assert secret, "CSRF protection requires a configured database secret"
        hm_expected = hmac.new(secret.encode('ascii'), msg.encode('utf-8'), hashlib.sha1).hexdigest()
        return consteq(hm, hm_expected)

    def http_dispatch(self, endpoint, args, auth):
        """ Handle ``http`` request type.

        Matched routing arguments, query string and form parameters (including
        files) are passed to the handler method as keyword arguments. In case
        of name conflict, routing parameters have priority.

        The handler method's result can be:

        * a falsy value, in which case the HTTP response will be an `HTTP 204`_ (No Content)
        * a werkzeug Response object, which is returned as-is
        * a ``str`` or ``unicode``, will be wrapped in a Response object and returned as HTML
        """

        # TODO why not use .values ?
        params = collections.OrderedDict(self.httprequest.args)
        params.update(self.httprequest.form)
        params.update(self.httprequest.files)
        # include args from route path parsing
        params.update(args)

        params.pop('session_id', None)
        self.params = params

        # TODO check else because this revert XMO 9e27956aa960dc9eea442418c83f5b3941b0c447
        # Check if it works with nodb
        # Reply to CORS requests if allowed
        if self.httprequest.method == 'OPTIONS' and endpoint.routing.get('cors'):
            headers = {
                'Access-Control-Max-Age': 60 * 60 * 24,
                'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept, Authorization'
            }
            return Response(status=200, headers=headers)


        # Check for CSRF token for relevant requests
        if request.httprequest.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE') and request.endpoint.routing.get('csrf', True):
            token = params.pop('csrf_token', None)
            if not self.validate_csrf(token):
                if token is not None:
                    _logger.warning("CSRF validation failed on path '%s'", request.httprequest.path)
                else:
                    _logger.warning("""No CSRF token provided for path '%s' https://www.odoo.com/documentation/13.0/reference/http.html#csrf for more details.""", request.httprequest.path)
                raise werkzeug.exceptions.BadRequest('Session expired (invalid CSRF token)')

        # ignore undefined extra args (utm, debug, ...)
        params_names = set(params)
        for p in inspect.signature(endpoint).parameters.values():
            if p.kind == inspect.Parameter.VAR_KEYWORD:
                # **kwargs catchall is defined
                break
            elif p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY) and p.name in params_names:
                params_names.remove(p.name)
        else:
            ignored = ['<%s=%s>' % (name, params.pop(name)) for name in params_names]
            _logger.debug("<function %s.%s> called ignoring args %s" % (endpoint.__module__, endpoint.__name__, ', '.join(ignored)))

        r = self._call_function(endpoint, **params)
        if not r:
            r = Response(status=204)  # no content
        elif isinstance(r, (bytes, str)):
            r = Response(response)
        #elif isinstance(r, werkzeug.exceptions.HTTPException):
        #    r = r.get_response(request.httprequest.environ)
        #elif isinstance(r, werkzeug.wrappers.BaseResponse):
        #    r = Response.force_type(r)
        #    r.set_default()
        return r

    #------------------------------------------------------
    # JSON-RPC2 Controllers
    #------------------------------------------------------
    def json_response(self, result=None, error=None, request_id=None):
        status = 200
        response = { 'jsonrpc': '2.0', 'id': request_id }
        if error is not None:
            response['error'] = error
            status = error.pop('http_status', 200)
        if result is not None:
            response['result'] = result

        body = json.dumps(response, default=date_utils.json_default)
        headers = [('Content-Type', 'application/json'), ('Content-Length', len(body))]

        return Response(body, status=status, headers=headers)

    def json_dispatch(self, endpoint, args, auth):
        """ Parser handler for `JSON-RPC 2 <http://www.jsonrpc.org/specification>`_ over HTTP

        * ``method`` is ignored
        * ``params`` must be a JSON object (not an array) and is passed as keyword arguments to the handler method
        * the handler method's result is returned as JSON-RPC ``result`` and wrapped in the `JSON-RPC Response <http://www.jsonrpc.org/specification#response_object>`_

        Sucessful request::

          --> {"jsonrpc": "2.0", "method": "call", "params": {"context": {}, "arg1": "val1" }, "id": null}

          <-- {"jsonrpc": "2.0", "result": { "res1": "val1" }, "id": null}

        Request producing a error::

          --> {"jsonrpc": "2.0", "method": "call", "params": {"context": {}, "arg1": "val1" }, "id": null}

          <-- {"jsonrpc": "2.0", "error": {"code": 1, "message": "End user error message.", "data": {"code": "codestring", "debug": "traceback" } }, "id": null}

        """
        json_request = self.httprequest.get_data().decode(self.httprequest.charset)
        try:
            self.jsonrequest = json.loads(json_request)
        except ValueError:
            _logger.info('%s: Invalid JSON data: %r', self.httprequest.path, json_request)
            raise werkzeug.exceptions.BadRequest()
        request_id = self.jsonrequest.get("id")
        params = dict(self.jsonrequest.get("params", {}))

        # Includes args from route path parsing
        params.update(args)
        # remove ?
        self.params = params

        self.context = params.pop('context', dict(self.session["context"]))

        # Call the endpoint
        t0 = self.rpc_debug_pre(endpoint, params)
        result = self._call_function(endpoint, **params)
        self.rpc_debug_post(t0, result)

        return self.json_response(result, request_id=request_id)

    #------------------------------------------------------
    # Handling
    #------------------------------------------------------
    def dispatch(self, endpoint, args, auth='none'):
        # save endpoint in self.endpoint for cors in response
        self.endpoint = endpoint
        # args are deducted by the route path parsing
        if endpoint.routing['type'] == 'http':
            r = self.http_dispatch(endpoint, args, auth)
        elif endpoint.routing['type'] == 'json':
            r = self.json_dispatch(endpoint, args, auth)
        return r

    def _handle_exception(self, exception):
        """Called within an except block to allow converting exceptions
           to abitrary responses. Anything returned (except None) will
           be used as response."""
        raise exception
        #self._failed = exception  # prevent tx commit
        #if not isinstance(exception, NO_POSTMORTEM) and not isinstance(exception, werkzeug.exceptions.HTTPException):
        #    odoo.tools.debugger.post_mortem( odoo.tools.config, sys.exc_info())


        ## WARNING: do not inline or it breaks: raise...from evaluates strictly
        ## LTR so would first remove traceback then copy lack of traceback
        #new_cause = Exception().with_traceback(exception.__traceback__)
        #new_cause.__cause__ = exception.__cause__
        ## tries to provide good chained tracebacks, just re-raising exception
        ## generates a weird message as stacks just get concatenated, exceptions
        ## not guaranteed to copy.copy cleanly & we want `exception` as leaf (for
        ## callers to check & look at)
        #raise exception.with_traceback(None) from new_cause

        ## HTTP
        #"""Called within an except block to allow converting exceptions
        #   to abitrary responses. Anything returned (except None) will
        #   be used as response."""
        #try:
        #    return super(HttpRequest, self)._handle_exception(exception)
        #except SessionExpiredException:
        #    if not request.params.get('noredirect'):
        #        query = werkzeug.urls.url_encode({ 'redirect': self.httprequest.url, })
        #        return werkzeug.utils.redirect('/web/login?%s' % query)

        #except werkzeug.exceptions.HTTPException as e:
        #    return e
        ## JSON

        #"""Called within an except block to allow converting exceptions
        #   to arbitrary responses. Anything returned (except None) will
        #   be used as response."""
        #try:
        #    return super(JsonRequest, self)._handle_exception(exception)
        #except Exception:
        #    if not isinstance(exception, SessionExpiredException):
        #        if exception.args and exception.args[0] == "bus.Bus not available in test mode":
        #            _logger.info(exception)
        #        elif isinstance(exception, (odoo.exceptions.Warning, odoo.exceptions.except_orm,
        #                                  werkzeug.exceptions.NotFound)):
        #            _logger.warning(exception)
        #        else:
        #            _logger.exception("Exception during JSON request handling.")
        #    error = {
        #        'code': 200,
        #        'message': "Odoo Server Error",
        #        'data': serialize_exception(exception),
        #    }
        #    if isinstance(exception, werkzeug.exceptions.NotFound):
        #        error['http_status'] = 404
        #        error['code'] = 404
        #        error['message'] = "404: Not Found"
        #    if isinstance(exception, AuthenticationError):
        #        error['code'] = 100
        #        error['message'] = "Odoo Session Invalid"
        #    if isinstance(exception, SessionExpiredException):
        #        error['code'] = 100
        #        error['message'] = "Odoo Session Expired"
        #    return self._json_response(error=error)

    def coerce_response(self, result):
        if result:
            if isinstance(result, (bytes, str)):
                # Use already existing
                self.response.set_data(result)
            else:
                if isinstance(result, Response) and result.is_qweb:
                    result.flatten()

                # Preserve self.response.headers
                for key in result.headers.keys():
                    values = result.headers.getlist(key)

                    values_iter = iter(values)
                    self.response.headers.set(key, next(values_iter))
                    for value in values_iter:
                        self.response.headers.add(key, value)

                result.headers = self.response.headers
                self.response = result

    def handle_static(self):
        path_info = werkzeug.wsgi.get_path_info(self.httprequest.environ)
        for prefix, directory in self.app.statics.items():
            #_logger.info('check %s %s',path_info, static)
            if path_info.startswith(prefix):
                suffix = path_info[len(prefix):]
                filename = werkzeug.security.safe_join(directory, suffix)
                try:
                    content = open(filename, "rb")
                except Exception:
                    raise werkzeug.exceptions.NotFound("File not found.\n")
                # TODO Honor DisableCacheMiddleware TODO implement DisableCacheMiddleware(app)
                # May we need to move to Request to do this as we need session
                #if req.session and req.session.debug and not 'wkhtmltopdf' in req.headers.get('User-Agent'):
                #    #if "assets" in req.session.debug and (".js" in req.base_url or ".css" in req.base_url):
                #    #    new_headers = [('Cache-Control', 'no-store')]
                #    #else:
                #    #    new_headers = [('Cache-Control', 'no-cache')]
                #    for k, v in headers:
                #        if k.lower() != 'cache-control':
                #            new_headers.append((k, v))
                return self.send_file(content)

    def handle(self):
            # Serve controllers
            # locate nodb controller first
            try:
                nodb_endpoint, nodb_args = self.app.nodb_routing_map.bind_to_environ(self.httprequest.environ).match()
            except (werkzeug.exceptions.NotFound, werkzeug.exceptions.MethodNotAllowed) as nodb_exception:
                nodb_endpoint = None
            # Thread local environments
            with odoo.api.Environment.manage():
                self.session_pre()
                # ir.http handling
                if self.db:
                    try:
                        if nodb_endpoint:
                            result = request.dispatch(nodb_endpoint, nodb_args, "none")
                        else:
                            result = self.env["ir.http"]._dispatch()
                        self.coerce_response(result)
                        # TODO proper commit and sign changes
                        #return request._handle_exception(e)
                        # finnaly
                        #def __exit__(self, exc_type, exc_value, traceback):
                        #    if self._cr:
                        #        try:
                        #            if exc_type is None and not self._failed:
                        #                self._cr.commit()
                        #                if self.registry:
                        #                    self.registry.signal_changes()
                        #            elif self.registry:
                        #                self.registry.reset_changes()
                        #        finally:
                        #            self._cr.close()
                        # release thread local request
                        _logger.info("session POSt")
                        self.session_post()
                        self.env.cr.commit()
                        self.env.registry.signal_changes()
                        return self.response
                    except Exception as e:
                        _logger.exception(e)
                        raise e
                # no db handling
                else:
                    if nodb_endpoint:
                        result = request.dispatch(nodb_endpoint, nodb_args, "none")
                    else:
                        result = nodb_exception
                    response = self.coerce_response(result)
                    return response

#----------------------------------------------------------
# WSGI Layer
#----------------------------------------------------------
class Application(object):
    """ WSGI application for Odoo. """
    def __init__(self):
        self.statics = None
        self.nodb_routing_map = None

    def proxy_mode(environ):
        # patch environ for proxy
        # FIXME: is checking for the presence of HTTP_X_FORWARDED_HOST really useful? we're ignoring the user configuration, and that means we won't support the standardised Forwarded header
        x_host = environ.get("HTTP_X_FORWARDED_HOST")
        if x_host:
            x_host_parts = x_host.split(":", 1)
            environ.update({
                "werkzeug.proxy_fix.orig": {
                    "REMOTE_ADDR": environ.get("REMOTE_ADDR"),
                    "wsgi.url_scheme": environ.get("wsgi.url_scheme"),
                    "HTTP_HOST": environ.get("HTTP_HOST"),
                    "SERVER_NAME": environ.get("SERVER_NAME"),
                    "SERVER_PORT": environ.get("SERVER_PORT"),
                },
                "REMOTE_ADDR": environ.get("HTTP_X_FORWARDED_FOR"),
                "wsgi.url_scheme": environ.get("HTTP_X_FORWARDED_PROTO"),
                "HTTP_HOST": x_host,
                "SERVER_NAME": x_host_parts[0],
            })
            if len(x_host_parts) == 2:
                environ["SERVER_PORT"] = xhost_parts[1]

    def setup_statics(self):
        """ Load all addons from addons path containing static files and
        controllers and configure them.  """
        self.statics = {}
        for addons_path in odoo.addons.__path__:
            for module in sorted(os.listdir(str(addons_path))):
                if module not in addons_manifest:
                    mod_path = os.path.join(addons_path, module)
                    manifest_path = module_manifest(mod_path)
                    path_static = os.path.join(addons_path, module, 'static')
                    if manifest_path and os.path.isdir(path_static):
                        with open(manifest_path, 'rb') as fd:
                            manifest_data = fd.read()
                        manifest = ast.literal_eval(pycompat.to_text(manifest_data))
                        if not manifest.get('installable', True):
                            continue
                        manifest['addons_path'] = addons_path
                        _logger.debug("Loading %s", module)
                        addons_manifest[module] = manifest
                        self.statics['/%s/static/' % module] = path_static

    def setup_nodb_routing_map(self):
        self.nodb_routing_map = werkzeug.routing.Map(strict_slashes=False, converters=None)
        for url, endpoint, routing in odoo.http._generate_routing_rules([''] + odoo.conf.server_wide_modules, True):
            rule = werkzeug.routing.Rule(url, endpoint=endpoint, methods=routing['methods'])
            rule.merge_slashes = False
            self.nodb_routing_map.add(rule)

    def __call__(self, environ, start_response):
        if odoo.tools.config['proxy_mode']:
            self.proxy_mode(environ)

        # Lazy load statics and routing map
        if not self.statics:
            self.setup_statics()
            self.setup_nodb_routing_map()
            _logger.info("HTTP Application configured")

        httprequest = werkzeug.wrappers.Request(environ)
        httprequest.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict
        request = Request(self, httprequest)
        _request_stack.push(request)
        try:
            response = request.handle_static() or request.handle()
            # TODO removed app on httprequest grep website and test_qweb request.httprequest.app.get_db_router(request.db)
        except werkzeug.exceptions.HTTPException as response_error:
            return response_error(environ, start_response)
        else:
            return response(environ, start_response)
        finally:
            _request_stack.pop()

# wsgi handler
application = root = Application()
#
