"""
Odoo HTTP layer

                         Request._dispatch_static
                       /
Application.__call__ -+- Request._dispatch_nodb                                -----------------------------------------
                       \                        \                             /                                         \
                        \                        \ / Request.http_dispatch \ /                                           \
                         \                        +                         +                                             +- route_wrapper - endpoint
                          \                      / \ Request.json_dispatch / \                                           /
                            Request._dispatch_db                               model.retrying - env['ir.http']._dispatch

Application.__call__
  WSGI entry point, it sanitizes the request, dispatches it (static,
  nodb or db) and is responsible of calling the WSGI ``start_response``
  callback. Internal reroutings (see :meth:``Request.reroute``) are
  performed here.

Request._dispatch_static
  Handle all requests to ``/<module>/static/<asset>`` paths, open the
  underlying file on the filesystem and stream it via
  :meth:``Request.send_file``

Request._dispatch_nodb
  Handle all requests to ``@route(auth='none')`` endpoints, it does not
  connect to the database nor open a session nor initializes an
  environment. If the underlying endpoint raises a redirection to the
  database selector then the request is re-dispatched to ``_dispatch_db``.

Request._dispatch_db
  Like _dispatch_nodb but connects to the database, open a session and
  initializes an environment. It delegates many operations to
  ``env['ir.http']._dispatch``

Request.http_dispatch
  Handle requests to ``@route(type='http')`` endpoints, gather the
  arguments from the path, the query string, the body forms and the body
  files. Performes cors and csrf checks.

Request.json_dispatch
  Handle requests to ``@route(type='json')`` endpoints, gather the
  arguments only from the path and the body.

service.model.retrying
  Only in the context of a ``_dispatch_db`` request. It is responsible
  of commiting the database cursor opened by ``_dispatch_db``, it is
  also responsible of retrying the request processing in case of a
  serialisation error (when two independant workers write on a same
  record at the same time).

env['ir.http']._dispatch
  Only in the context of a ``_dispatch_db`` request. It just calls the
  route endpoint when no other modules than base is installed. Other
  modules and override the method and act as middleware. See also the
  ``env['ir.http']._pre_dispatch`` method.

route_wrapper, closure of the http.route decorator
  Sanitize the request parameters, call the route endpoint and 
  optionaly coerce the endpoint result.

endpoint
  The @route(...) decorated method.
"""

import ast
import base64
import collections
import contextlib
import datetime
import functools
import hashlib
import hmac
import inspect
import io
import json
import logging
import mimetypes
import os
import pprint
import random
import re
import secrets
import sys
import threading
import time
import traceback
import urllib.parse
import warnings
import zlib
from os.path import join as opj

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
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError
try:
    from werkzeug.middleware.proxy_fix import ProxyFix as ProxyFix_
    ProxyFix = functools.partial(ProxyFix_, x_for=1, x_proto=1, x_host=1)
except ImportError:
    from werkzeug.contrib.fixers import ProxyFix

# Optional psutil, not packaged on windows
try:
    import psutil
except ImportError:
    psutil = None

import odoo
from .exceptions import UserError
from .modules.module import read_manifest
from .modules.registry import Registry
from .service.server import memory_info
from .service import security, model as service_model
from .sql_db import db_connect
from .tools import (config, ustr, consteq, frozendict, pycompat, unique,
                    date_utils, DotDict, resolve_attr, submap)
from .tools.mimetypes import guess_mimetype
from .tools.func import filter_kwargs, lazy_property


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

# ... (three months)
SESSION_LIFETIME = 90 * 24 * 60 * 60

# When loading the session from the database into the request.session
# attribute, what keys are unsafe and should be returned in a distinct
# dictionnary instead of being set on request.session.
UNSAFE_SESSION_KEYS = {'uid', 'context'}

# How many time is it allowed to raise Reroute()
MAX_REROUTING = 10

# The @route keys to propagate from the decorated method to the routing rule
ROUTING_KEYS = {
    'defaults', 'subdomain', 'build_only', 'strict_slashes', 'redirect_to',
    'alias', 'host', 'methods',
}

old_redirect_msg = """
The request.redirect() signature changed, you set the query string right
in the path, you should instead use the new "query" argument. You can
rewrite your code as follow:

    request.redirect({path}, {query}, code={code})

"""

#----------------------------------------------------------
# Helpers
#----------------------------------------------------------

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


def db_list(force=False):
    if odoo.tools.config['db_name']:
        return [db.strip() for db in odoo.tools.config['db_name'].split(',')]

    if odoo.tools.config['dbfilter']:
        host = request.httprequest.environ.get('HTTP_HOST', '')
        domain = host.removeprefix('www.').partition('.')[0]
        dbfilter_re = re.compile(
            odoo.tools.config['dbfilter']
                .replace('%h', re.escape(host))
                .replace('%d', re.escape(domain))
        )
        all_dbs = odoo.service.db.list_dbs(force=True)
        return [db for db in all_dbs if dbfilter_re.match(db)]

    return odoo.service.db.list_dbs(force=True)

def send_file(*args, **kwargs):
    warnings.warn(
        "http.send_file is a deprecated alias to http.request.send_file",
        DeprecationWarning, stacklevel=2)
    return request.send_file(*args, **kwargs)


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
            _logger.debug('controller %r %r %r', module, name, bases)

Controller = ControllerType('Controller', (object,), {})

def route(route=None, **routing):
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
    def decorator(endpoint):
        fname = f"<function {endpoint.__module__}.{endpoint.__name__}>"

        assert 'type' not in routing or routing['type'] in ('http', 'json')
        if route:
            routing['routes'] = route if isinstance(route, list) else [route]
        if wrong := routing.pop('method', None):
            _logger.warning("%s defined with invalid routing parameter 'method', assuming 'methods'", fname)
            routing['methods'] = wrong

        @functools.wraps(endpoint)
        def route_wrapper(self, **params):
            params_ok = filter_kwargs(endpoint, params)
            if params_ko := set(params) - set(params_ok):
                _logger.debug("%s called ignoring args %s", fname, params_ko)

            result = endpoint(self, **params_ok)

            if routing['type'] == 'http':  # _generate_routing_rules() ensures type is set
                return Response.load(result, fname=fname)
            return result

        route_wrapper.original_routing = routing
        route_wrapper.original_endpoint = endpoint
        return route_wrapper
    return decorator


def _generate_routing_rules(modules, nodb_only, converters=None):
    classes = []
    for module in modules:
        classes += controllers.get(module, [])

    # We lack a proper registry for controllers, for now sorting the
    # classes by number of inheritance and skipping already-seen classes
    # is enough.
    classes.sort(key=lambda c: len(c.__mro__), reverse=True)
    seen = set()

    for Controller in classes:
        for method_name, method in inspect.getmembers(Controller(), inspect.ismethod):
            if f'{Controller.__module__}.{Controller.__name__}.{method_name}' in seen:
                continue

            # Skip this method if it is a regular method not @route
            # decorated anywhere in the hierarchy
            def is_method_a_route(ctrl):
                return resolve_attr(ctrl, f'{method_name}.original_routing', None) is not None
            if not any(map(is_method_a_route, Controller.__mro__)):
                continue

            merged_routing = {
                #'type': 'http',  # set below
                'auth':'user',
                'methods': None,
                'routes':None,
                'readonly':False,
            }

            for ctrl in reversed(Controller.__mro__):  # ancestors first
                fullname = f'{ctrl.__module__}.{ctrl.__name__}.{method_name}'
                seen.add(fullname)
                submethod = getattr(ctrl, method_name, None)
                if submethod is None:
                    continue

                if not hasattr(submethod, 'original_routing'):
                    _logger.warning("The endpoint %s is not decorated by @route(), decorating it myself.", fullname)
                    submethod = route()(submethod)

                # Ensure "type" is defined on each method's own routing, also
                # ensure overrides don't change the routing type.
                default_type = submethod.original_routing.get('type', 'http')
                routing_type = merged_routing.setdefault('type', default_type)
                if submethod.original_routing.get('type') not in (None, routing_type):
                    _logger.warning("The endpoint %s changes the route type, using the original type: %r.", fullname, routing_type)
                submethod.original_routing['type'] = routing_type

                merged_routing.update(submethod.original_routing)

            if merged_routing['routes'] is None:
                _logger.warning("The method %s in %s.%s is a web endpoint without any route, skipping.", method_name, ctrl.__module__, ctrl.__name__)
                continue

            if nodb_only and merged_routing['auth'] != "none":
                continue

            for url in merged_routing['routes']:
                endpoint = functools.partial(method)  # same fonction, new namespace
                endpoint.routing = merged_routing
                endpoint.original_endpoint = method.original_endpoint
                endpoint.original_routing = method.original_routing
                yield (url, endpoint)

def serialize_exception(exception):
    name = type(exception).__name__
    module = type(exception).__module__

    return {
        'name': f'{module}.{name}' if module else name,
        'debug': traceback.format_exc(),
        'message': ustr(exception),
        'arguments': exception.args,
        'context': getattr(exception, 'context', {}),
    }

#----------------------------------------------------------
# Request and Response
#----------------------------------------------------------
# Thread local global request object
_request_stack = werkzeug.local.LocalStack()
# global proxy that always redirect to the thread local request object.
request = _request_stack()

class SessionExpiredException(Exception):
    pass

class Reroute(Exception):
    """ Restart the entire request processing using a new URL. """

    def __init__(self, path, save_session, request_attrs):
        if any(req.path == new_path for req in _request_stack._local.stack):
            raise ValueError("Rerouting loop is forbidden")

        self.path = path
        self.commit_session = commit_session
        self.request_attrs = request_attrs
        super().__init__(self, path, query, save_session, request_attrs)

class Response(werkzeug.wrappers.Response):
    """ Response object passed through controller route chain.

    In addition to the :class:`werkzeug.wrappers.Response` parameters,
    this class's constructor can take the following additional
    parameters for QWeb Lazy Rendering.

    :param basestring template: template to render
    :param dict qcontext: Rendering context to use
    :param int uid: User id to use for the ir.ui.view render call,
                    ``None`` to use the request's user (the default)

    these attributes are available as parameters on the Response object
    and can be altered at any time before rendering

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

    @classmethod
    def load(cls, result, fname):
        """
        Load a response from ``result``.

        :param Any result: the endpoint return value to load the Response from
        :param str fname: the enpoint function name, used for logging
        """
        if isinstance(result, Response):
            return result

        if isinstance(result, werkzeug.exceptions.HTTPException):
            _logger.warning("%s returns an HTTPException instead of raising it.", fname)
            raise result

        if isinstance(result, werkzeug.wrappers.BaseResponse):
            response = cls.force_type(result)
            response.set_default()
            return response

        if isinstance(result, (bytes, str, type(None))):
            return cls(result)

        raise TypeError("%s returns an invalid value: %s", fname, result)

    def set_default(self, template=None, qcontext=None, uid=None):
        self.template = template
        _logger.info("reponse template %s",self.template)
        self.qcontext = qcontext or dict()
        self.qcontext['response_template'] = self.template
        self.uid = uid

        # Support for Cross-Origin Resource Sharing
        if 'cors' in (routing := resolve_attr(request, 'endpoint.routing', {})):
            self.headers.set('Access-Control-Allow-Origin', routing['cors'])
            self.headers.set('Access-Control-Allow-Methods', (
                     'POST' if routing['type'] == 'json'
                else ', '.join(routing.get('methods', ['GET', 'POST']))
            ))

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
    def __init__(self, app, httprequest, routing_iteration):
        self.app = app
        self.httprequest = httprequest
        self.params = {}
        self.routing_iteration = routing_iteration

        # Session
        self.session = DotDict()
        self.session_id = None
        self.session_touch = False  # bad wording
        self._session_data = None

        # Environment
        self.db = None
        self.env = None

        # Response
        self.response_headers = werkzeug.datastructures.Headers()

    #------------------------------------------------------
    # Getters and setters
    #------------------------------------------------------

    def update_env(self, user=None, context=None, su=None):
        self.env = self.env(None, user, context, su)

    def update_context(self, **overrides):
        """ Override the current request environment context by the
        values of ``overrides``.
        """
        self.update_env(context=dict(self.env.context, **overrides))

    @property
    def context(self):
        warnings.warn('Deprecated alias to request.env.context', DeprecationWarning, stacklevel=2)
        return self.env.context

    @context.setter
    def context(self, value):
        raise NotImplementedError("Use request.update_context instead.")

    @property
    def uid(self):
        warnings.warn('Deprecated alias to request.env.uid', DeprecationWarning, stacklevel=2)
        return self.env.uid

    @uid.setter
    def uid(self, value):
        raise NotImplementedError("Use request.update_env instead.")

    @property
    def cr(self):
        warnings.warn('Deprecated alias to request.env.cr', DeprecationWarning, stacklevel=2)
        return self.env.cr

    @cr.setter
    def cr(self, value):
        if value is None:
            raise NotImplementedError("Close the cursor instead.")
        raise NotImplementedError("Use request.update_env instead.")

    _cr = cr

    #------------------------------------------------------
    # Common helpers
    #------------------------------------------------------

    def send_filepath(self, path, **send_file_kwargs):
        fd = open(path, 'rb')  # closed by werkzeug
        return self.send_file(fd, **send_file_kwargs)

    def send_file(self, file, filename=None, mimetype=None, mtime=None, as_attachment=False, cache_timeout=STATIC_CACHE):
        """Send file, str or bytes content with mime and cache handling.

        Sends the contents of a file to the client.  Using werkzeug file_wrapper
        support.

        If filename of file.name is provided it will try to guess the mimetype
        for you, but you can also explicitly provide one.

        :param file : fileobject to read from or str or bytes.
        :param filename: optional if file has a 'name' attribute, used for attachment name and mimetype guess (i.e. io.BytesIO)
        :param mimetype: the mimetype of the file if provided, otherwise auto detection happens based on the name.
        :param mtime: optional if file has a 'name' attribute, last modification time used for contitional response.
        :param as_attachment: set to `True` if you want to send this file with a ``Content-Disposition: attachment`` header.
        :param cache_timeout: set to `False` to disable etags and conditional response handling (last modified and etags)
        """

        # REM for odo i removed the unsafe path api
        if isinstance(file, str):
            file = file.encode('utf8')
        if isinstance(file, bytes):
            file = io.BytesIO(file)

        # Only used when filename or mtime argument is not provided
        path = getattr(file, 'name', 'file.bin')

        if not filename:
            filename = os.path.basename(path)

        if not mimetype:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        if not mtime:
            try:
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
            except Exception:
                pass

        file.seek(0, 2)
        size = file.tell()
        file.seek(0)

        data = werkzeug.wsgi.wrap_file(self.httprequest.environ, file)

        res = werkzeug.wrappers.Response(data, mimetype=mimetype, direct_passthrough=True)
        res.content_length = size

        if as_attachment:
            res.headers.add('Content-Disposition', 'attachment', filename=filename)

        if cache_timeout:
            if mtime:
                res.last_modified = mtime
            crc = zlib.adler32(filename.encode('utf-8') if isinstance(filename, str) else filename) & 0xffffffff
            etag = 'odoo-%s-%s-%s' % ( mtime, size, crc)
            if not werkzeug.http.is_resource_modified(self.httprequest.environ, etag, last_modified=mtime):
                res = werkzeug.wrappers.Response(status=304)
            else:
                res.cache_control.public = True
                res.cache_control.max_age = cache_timeout
                # expires is deprecated
                #r.expires = int(time.time() + cache_timeout)
                res.set_etag(etag)
        _logger.info("response %s", res)
        return res

    def default_lang(self):
        lang = self.httprequest.accept_languages.best or "en-US"
        try:
            code, territory, _, _ = babel.core.parse_locale(lang, sep='-')
            if territory:
                lang = f'{code}_{territory}'
            else:
                lang = babel.core.LOCALE_ALIASES[code]
        except (ValueError, KeyError):
            lang = 'en_US'

        return lang

    def set_thread_info(self, session_uid):
        th = threading.current_thread()
        th.dbname = self.db
        th.uid = session_uid
        th.url = self.httprequest.url
        th.query_count = 0
        th.query_time = 0
        th.perf_t0 = time.time()

    def _reraise_fixing_traceback(self, exception):
        # WARNING: do not inline or it breaks: raise...from evaluates strictly
        # LTR so would first remove traceback then copy lack of traceback
        new_cause = Exception().with_traceback(exception.__traceback__)
        new_cause.__cause__ = exception.__cause__
        # tries to provide good chained tracebacks, just re-raising exception
        # generates a weird message as stacks just get concatenated, exceptions
        # not guaranteed to copy.copy cleanly & we want `exception` as leaf (for
        # callers to check & look at)
        raise exception.with_traceback(None) from new_cause

    @contextlib.contextmanager
    def debug_rpc(self, endpoint, params, model=None, method=None):
        # For Odoo service RPC params is a list or a tuple, for call_kw style it is a dict
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

        result_placeholder = [None]
        yield result_placeholder
        result = result_placeholder[0]

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
        except (odoo.exceptions.UserError, odoo.exceptions.RedirectWarning):
            # don't trigger debugger for those exceptions, they carry
            # user-facing warnings and indications, they're not
            # necessarily indicative of anything being *broken*
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
    def get_session_id(self):
        sid, _, requested_db = (
               self.httprequest.args.get('session_id')
            or self.httprequest.headers.get("X-Openerp-Session-Id")
            or self.httprequest.cookies.get('session_id')
            or ''
        ).partition('.')
        query_db = self.httprequest.args.get('db')
        if query_db:
            requested_db = query_db

        available_dbs = db_list(force=True)
        if requested_db in available_dbs:
            return sid, requested_db
        if len(available_dbs) == 1:
            return sid, available_dbs[0]
        return sid, None


    @contextlib.contextmanager
    def manage_session(self, sid, dbname):
        db = db_connect(dbname)
        if not sid:
            sid = secrets.token_urlsafe()  # use 32 bytes of entropy as of Py3.10
        self.response.set_cookie('session_id', f'{sid}.{self.db}', max_age=SESSION_LIFETIME, httponly=True)

        # Load the session from the database
        with contextlib.closing(db.cursor()) as cr:
            cr.execute("SELECT data FROM ir_session WHERE sid = %s", (sid,))
            row = cr.fetchone()
            if row:
                self.session_touch = False
                self._session_data = row[0]
            else:
                self.session_touch = True
                self._session_data = json.dumps({
                    'context': {},
                    'debug': '',
                    'login': None,
                    'uid': None,
                    'sid': sid,
                })

        def save_session():
            with db.cursor() as cr:
                cr.execute("""
                    INSERT INTO ir_session (sid, data, create_date, write_date)
                    VALUES (%(sid)s, %(data)s, NOW(), NOW())
                    ON CONFLICT (sid)
                        DO UPDATE SET data=%(data)s, write_date=NOW()
                """, {
                    'sid': sid,
                    'data': json.dumps(self.session, ensure_ascii=False, sort_keys=True),
                })

        self.session = DotDict(json.loads(self._session_data))
        try:
            yield
        except Reroute as exc:
            if exc.save_session:
                save_session()
            raise

        if self.session_touch or json.dumps(self.session) != self._session_data:
            save_session()


    def reload_session(self):
        self.session = DotDict(json.loads(self._session_data))
        self.update_env(self, self.env.cr, self.session.uid, self.session.context)

    def session_authenticate_start(self, login=None, password=None):
        """ Authenticate the current user with the given db, login and
        password. If successful, store the authentication parameters in the
        current session and request, unless multi-factor-authentication is
        activated. In that case, that last part will be done by
        :ref:`session_authenticate_finalize`.
        """
        wsgienv = {
            "interactive" : True,
            "base_location" : self.httprequest.url_root.rstrip('/'),
            "HTTP_HOST" : self.httprequest.environ['HTTP_HOST'],
            "REMOTE_ADDR" : self.httprequest.environ['REMOTE_ADDR'],
        }
        uid = self.env['res.users'].authenticate(self.db, login, password, wsgienv)
        _logger.info("UID %s",uid)

        self.session['pre_login'] = login
        self.session['pre_uid'] = uid

        # if 2FA is disabled we finalize immediatly
        user = self.env(user=uid)['res.users'].browse(uid)
        if not user._mfa_url():
            self.session_authenticate_finalize()

    def session_authenticate_finalize(self):
        """ Finalizes a partial session, should be called on MFA validation to
        convert a partial / pre-session into a full-fledged "logged-in" one """
        self.session.login = self.session.pop('pre_login')
        uid = self.session.pop('pre_uid')
        self.session.uid = uid
        self.update_env(user=uid)
        threading.current_thread().uid = uid


    #------------------------------------------------------
    # HTTP Controllers
    #------------------------------------------------------
    def redirect(self, location, *, query=frozendict(), fragment=frozendict(),
                 code=303, external=False):
        """ Abort the current request and redirect the user's browser
        on the new location.

        :param str location: the new url where the user is redirected
        :param Mapping query: the query pairs to inject in the new url
        :param Mapping fragment: the fragment pairs to inject in the new
          url
        :param int code: the http status code of the redirection
        :param bool external: flag to allow a redirection to an external
          website
        """
        url = werkzeug.urls.url_parse(location)
        url = url.replace(
            scheme=url.scheme if external else '',
            netloc=url.netloc if external else '',
            query=werkzeug.urls.url_encode(
                werkzeug.urls.url_decode(url.query) | query),
            fragment=werkzeug.urls.url_encode(
                werkzeug.urls.url_decode(url.fragment) | fragment),
        )
        location = url.to_url()

        if self.db:
            return self.env['ir.http']._redirect(location, code)
        return werkzeug.utils.redirect(location, code, Response=Response)

    def redirect(self, location, code=303, local=True):
        # compatibility, Werkzeug support URL as location
        if isinstance(location, urls.URL):
            location = location.to_url()
        if local:
            location = urls.url_parse(location).replace(scheme='', netloc='').to_url()
        if self.db:
            return self.env['ir.http']._redirect(location, code)
        return werkzeug.utils.redirect(location, code, Response=Response)

    def redirect_query(self, location, query=None, code=303, local=True):
        if query:
            location += '?' + urls.url_encode(query)
        return self.redirect(location, code=code, local=local)

    def reroute(self, path, *, query=frozendict(), save_session=False,
                      request_attrs=frozendict()):
        """ Restart the request processing using the new path.

        :param str path: the new path that replaces the current one.
        :param Mapping query: the query string to inject in the new path
        :param bool commit_session: whether the current draft session
          should be discarded (default) or saved.
        :param Mapping request_attrs: attributes to set on the new
          updated request. Use it to preserve attributes from the
          current request on the new one.

        :raise ValueError: in case ``path`` have been visited already to
          prevent loops.
        """
        qs = werkzeug.urls.url_encode(query)
        raise Reroute(f'{path}?{qs}', save_session, request_attrs)

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
        return NotFound(description)

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
        # if no `time_limit` => distant 1y expiry (31536000) so max_ts acts as salt, e.g. vs BREACH
        max_ts = int(time.time() + (time_limit or 31536000))

        msg = f'{self.session_id}{max_ts}'
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        if not secret:
            raise ValueError("CSRF protection requires a configured database secret")
        hm = hmac.new(secret.encode('ascii'), msg.encode('utf-8'), hashlib.sha1).hexdigest()
        return f'{hm}o{max_ts}'

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

        token = self.session_id

        msg = f'{token}{max_ts}'
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        if not secret:
            raise ValueError("CSRF protection requires a configured database secret")
        hm_expected = hmac.new(secret.encode('ascii'), msg.encode('utf-8'), hashlib.sha1).hexdigest()
        return consteq(hm, hm_expected)

    def http_dispatch(self, endpoint, args):
        """ Handle ``http`` request type.

        Matched routing arguments, query string and form parameters (including
        files) are passed to the handler method as keyword arguments. In case
        of name conflict, routing parameters have priority.

        The handler method's result can be:

        * a falsy value, in which case the HTTP response will be an `HTTP 204`_ (No Content)
        * a werkzeug Response object, which is returned as-is
        * a ``str`` or ``unicode``, will be wrapped in a Response object and returned as HTML
        """
        self.params = dict(
            self.httprequest.args,
            **self.httprequest.form,
            **self.httprequest.files,
            **args,
        )
        self.params.pop('session_id', None)

        # TODO check else because this revert XMO 9e27956aa960dc9eea442418c83f5b3941b0c447
        # Check if it works with nodb
        # Reply to CORS requests if allowed
        # JUC, funny: community/addons/hw_drivers/http.py
        if self.httprequest.method == 'OPTIONS' and endpoint.routing.get('cors'):
            headers = {
                'Access-Control-Max-Age': 60 * 60 * 24,
                'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept, Authorization'
            }
            return Response(status=200, headers=headers)

        # Check for CSRF token for relevant requests
        if request.httprequest.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE') and endpoint.routing.get('csrf', True):
            if not self.db:
                # In case of @route(auth='none', csrf=True), we first try to
                # dispatch the route via _nodb_dispatch which is wrong as we
                # need the database to retrieve the token, we raise a NotFound
                # http error so the requests is re-dispatch to _db_dispatch.
                raise NotFound(f"The {self.httprequest.path} url requires a database.")

            token = params.pop('csrf_token', None)
            if not self.validate_csrf(token):
                if token is not None:
                    _logger.warning("CSRF validation failed on path '%s'", request.httprequest.path)
                else:
                    _logger.warning("""No CSRF token provided for path '%s' https://www.odoo.com/documentation/13.0/reference/http.html#csrf for more details.""", request.httprequest.path)
                raise werkzeug.exceptions.BadRequest('Session expired (invalid CSRF token)')

        return endpoint(**self.params)

    def http_handle_error(self, exc):
        if isinstance(exc, SessionExpiredException):
            return self.redirect('/web/login?' + werkzeug.urls.url_encode({
                'redirect': (
                    f'/web/proxy/post{self.httprequest.full_path}'
                    if self.httprequest.method == 'POST'
                    else self.httprequest.url
                )
            }))

        _logger.error("Exception during HTTP request handling.", exc_info=exc)
        try:
            new_cause = InternalServerError().with_traceback(exc.__traceback__)
            new_cause.__cause__ = exc.__cause__
            raise new_cause.with_traceback(None) from exc
        except InternalServerError as exc_:
            return exc_

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

    def json_dispatch(self, endpoint, args):
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
        self.request_id = self.jsonrequest.get("id")
        self.params = dict(self.jsonrequest.get("params", {}), **args)
        if ctx := self.params.pop('context', None) is not None:
            self.update_context(ctx)

        # Call the endpoint
        debug_flag = _logger_rpc_request_flag or _logger_rpc_response_flag
        if debug_flag:
            with self.debug_rpc(endpoint, params) as result_placeholder:
                result = endpoint(**self.params)
                result_placeholder[0] = result
        else:
            result = endpoint(**self.params)

        return self.json_response(result, request_id=self.request_id)

    def json_handle_error(self, exc):
        if exc.args and exc.args[0] == "bus.Bus not available in test mode":
            _logger.info(exc)
        elif isinstance(exc, (UserError, NotFound)):
            _logger.warning(exc)
        else:
            _logger.error("Exception during JSON request handling.", exc_info=exc)

        error = {
            'code': 200,  # this code is the JSON-RPC level code, it is
                          # distinct from the HTTP status code. This
                          # code is ignored and the value 200 (while
                          # misleading) is totally arbitrary.
            'message': "Odoo Server Error",
            'data': serialize_exception(exc),
        }
        if isinstance(exc, NotFound):
            error['http_status'] = 404
            error['code'] = 404
            error['message'] = "404: Not Found"
        elif isinstance(exception, SessionExpiredException):
            error['code'] = 100
            error['message'] = "Odoo Session Expired"

        return self.json_response(
            error=error,
            request_id=getattr(self, 'request_id', None)
        )

    #------------------------------------------------------
    # Handling
    #------------------------------------------------------

    def _dispatch_static(self):
        module, _, path = self.httprequest.path.removeprefix('/').partition('/static/')
        try:
            directory = self.app.statics[module]
            filepath = werkzeug.security.safe_join(directory, path)
            return self.send_filepath(filepath)
        except KeyError:
            raise NotFound(f'Module "{module}" not found.\n')
        except OSError:
            raise NotFound(f'File "{path}" not found in module {module}.\n')

    def _dispatch_nodb(self):
        nodb_rule, nodb_args = self.app.nodb_routing_map.bind_to_environ(self.httprequest.environ).match(return_rule=True)
        reqtype = nodb_rule.endpoint.routing['type']
        dispatch = getattr(self, f'{reqtype}_dispatch')
        handle_error = getattr(self, f'{reqtype}_handle_error')
        try:
            response = dispatch(nodb_rule.endpoint, nodb_args)
        except HTTPException:
            raise
        except Exception as exc:
            if 'werkzeug' in config['dev_mode']:
                raise  # bubble up to werkzeug.debug.DebuggedApplication
            return handle_error(exc)

        response.headers.extend(self.response_headers)
        return response

    def _dispatch_db(self, session_id, dbname):
        self.session_id = session_id
        self.db = threading.current_thread().dbname = dbname

        # Session and cursor
        with odoo.api.Environment.manage(), \
             self.manage_session(session_id, dbname), \
             contextlib.closing(db_connect(dbname).cursor()) as cr:

            # Registry and Environment
            try:
                self.registry = Registry(dbname)
                self.registry.check_signaling()
            except (AttributeError, psycopg2.OperationalError, psycopg2.ProgrammingError) as e:
                # psycopg2 error or attribute error while constructing
                # the registry. That means either
                #  - the database probably does not exists anymore, or
                #  - the database is corrupted, or
                #  - the database version doesnt match the server version.
                # So remove the database from the cookie
                response = werkzeug.utils.redirect('/web/database/selector')
                response.set_cookie('session_id', session_id, max_age=SESSION_LIFETIME, httponly=True)
                response.headers.extend(self.response_headers)
                werkzeug.exceptions.abort(response)  # it raises

            self.env = odoo.api.Environment(cr, self.session.uid, self.session.context)

            # ir.http
            ir_http = self.env['ir.http']
            try:
                rule, args = ir_http._match(self.httprequest.path)
            except NotFound:  # maybe add odoo.exceptions.AccessError
                if response := ir_http._serve_fallback():
                    response.headers.extend(self.response_headers)
                    return response
                raise

            endpoint = self._inject_middlewares(rule.endpoint)
            dispatch = f"{endpoint.routing['type']}_dispatch"
            handle_error = f"{endpoint.routing['type']}_handle_error"

            try:
                ir_http._authenticate(endpoint)
                ir_http._pre_dispatch(rule, args)  # JUC, not retrying-protected
                response = getattr(request, dispatch)(endpoint, args)
            except HTTPException as response:
                response.headers.extend(self.response_headers)
                raise
            except Exception as exc:
                if 'werkzeug' in config['dev_mode']:
                    raise  # bubble up to werkzeug.debug.DebuggedApplication
                return getattr(request, handle_error)(exc)

            response.headers.extend(self.response_headers)
            return response

    def _inject_middlewares(self, rule_endpoint, **middlewares):
        """ Wrap the endpoint in several db-only middlewares """

        # retrying and ir_http._dispatch are optional middlewares, they
        # are only executed in the context of a dispatch to a database
        # controller after Request.(http|json)_dispatch() but before the
        # rule endpoint. Using partial to reduce the call stack size.
        #
        # nodb call order: Request.(http|json)_dispatch() -> rule_endpoint
        # db call order: Request.(http|json)_dispatch() -> retrying -> ir_http -> rule_endpoint
        #
        # Below is an example route with every function definition and
        # the 
        #
        #   class Request:
        #       def _http_dispatch(self, endpoint):       # endpoint = service_model.retrying
        #           params = {...}
        #           return endpoint(**params)
        #  
        #   def retrying(endpoint, **params):             # endpoint = env['ir.http']._dispatch
        #       return endpoint(**params)
        #  
        #   class IrHttp(models.Model):
        #       _name = 'ir.http'
        #       def _dispatch(self, endpoint, **params):  # endpoint = route_wrapper = rule_endpoint
        #           return endpoint(**params)
        #  
        #   def route(**routing)
        #       def decorator(endpoint):                  # endpoint = example_route = rule_endpoint.original_endpoint
        #           def route_wrapper(**params):
        #               return endpoint(**params)
        #           return route_wrapper
        #       return decorator
        #  
        #   @route('/example', type='http', auth='user')
        #   def example_route():
        #       return 'example'

        new_endpoint = rule_endpoint
        for middleware in (ir_http._dispatch, service_model.retrying):
            new_endpoint = functools.partial(middleware, new_endpoint)
            new_endpoint.routing = rule_endpoint.routing
            new_endpoint.original_routing = rule_endpoint.original_routing
            new_endpoint.original_endpoint = rule_endpoint.original_endpoint

        return new_endpoint


#----------------------------------------------------------
# WSGI Layer
#----------------------------------------------------------
class Application(object):
    """ WSGI application for Odoo. """

    @lazy_property
    def statics(self):
        """ Load all addons from addons path containing static files and
        controllers and configure them.  """

        statics = {}
        for addons_path in odoo.addons.__path__:
            for module in sorted(os.listdir(str(addons_path))):
                if module not in addons_manifest:
                    mod_path = opj(addons_path, module)
                    manifest = read_manifest(addons_path, module)
                    if not manifest or (not manifest.get('installable', True) and 'assets' not in manifest):
                        continue
                    manifest['addons_path'] = addons_path
                    addons_manifest[module] = manifest
                    path_static = opj(addons_path, module, 'static')
                    if os.path.isdir(path_static):
                        _logger.debug("Loading %s", module)
                        statics[module] = path_static

        return statics

    @lazy_property
    def nodb_routing_map(self):
        nodb_routing_map = werkzeug.routing.Map(strict_slashes=False, converters=None)
        for url, endpoint in _generate_routing_rules([''] + odoo.conf.server_wide_modules, nodb_only=True):
            rule = werkzeug.routing.Rule(url, endpoint=endpoint, **submap(endpoint.routing, ROUTING_KEYS))
            rule.merge_slashes = False
            nodb_routing_map.add(rule)

        return nodb_routing_map

    def prepare(self, environ):
        current_thread = threading.current_thread()
        current_thread.query_count = 0
        current_thread.query_time = 0
        current_thread.perf_t0 = time.time()

        if odoo.tools.config['proxy_mode'] and environ.get("HTTP_X_FORWARDED_HOST"):
            # The ProxyFix middleware has a side effect of updating the environ
            # see https://github.com/pallets/werkzeug/pull/2184
            def fake_app(environ, start_response):
                return []
            def fake_start_response(status, headers):
                return
            ProxyFix(fake_app)(environ, fake_start_response)

    def __call__(self, environ, start_response):
        self.prepare(environ)
        reroute_request_attrs = dict()

        try:
            for routing_iteration in range(1, MAX_REROUTING + 1):

                # Wrap the WSGI environ in a fancy Request and expose it
                httprequest = werkzeug.wrappers.Request(environ)
                httprequest.parameter_storage_class = (
                    werkzeug.datastructures.ImmutableOrderedMultiDict)
                threading.current_thread().url = httprequest.url

                if httprequest.method == 'GET' and '//' in httprequest.path:
                    return werkzeug.utils.redirect('{}?{}'.format(
                        httprequest.path.replace('//', '/'),
                        httprequest.query_string.decode('utf-8')
                    ), 301)

                request = Request(self, httprequest, routing_iteration)
                for attr, value in reroute_request_attrs.items():
                    setattr(request, attr, value)
                _request_stack.push(request)

                # Dispatch the request to its corresponding controller
                try:
                    segments = httprequest.path.split('/')
                    if len(segments) >= 4 and segments[2] == 'static':
                        response = request._dispatch_static()
                        return response(environ, start_response)

                    sid, dbname = request.get_session_id()
                    try:
                        response = request._dispatch_nodb()
                        return response(environ, start_response)
                    except HTTPException as exc:
                        # Error in _dispatch_nodb. In case of a 404 or a
                        # redirection to the db selector, there is a chance
                        # the endpoint can be reached by _dispatch_db
                        if not dbname:
                            raise
                        if (exc.code != 404
                            and resolve_attr(exc, 'response.location', '')
                                != '/web/database/selector'):
                            raise
                    
                    response = request._dispatch_db(sid, dbname)
                    return response(environ, start_response)

                # Internal rerouting, update the original environ with
                # the new path and loop, creating a new request with the
                # updated environ.
                except Reroute as reroute:
                    _logger.info('Internal rerouting of %s to %s', request.path, reroute.path)
                    environ['PATH_INFO'] = reroute.path
                    reroute_request_attrs = reroute.request_attrs

                # Explicit "raise werkzeug.exception.NotFound()" like
                # exception or error programming error caught and casted
                # by request.(http|json)_handle_error()
                except HTTPException as response_error:
                    return response_error(environ, start_response)

                # Programming error in http.py
                except Exception as exc:
                    if 'werkzeug' in config['dev_mode']:
                        raise  # bubble up to werkzeug.debug.DebuggedApplication
                    response_error = request.http_handle_error(exc)
                    return response_error(environ, start_response)

            return NotFound("Too many internal reroutings")(environ, start_response)
        finally:
            while _request_stack.top:
                _request_stack.pop()


# wsgi handler
app = application = root = Application()
