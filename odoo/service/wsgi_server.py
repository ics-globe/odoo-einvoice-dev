# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""

WSGI stack, common code.

"""

import logging
import sys
import threading
import traceback

from xmlrpc import client as xmlrpclib

import werkzeug.exceptions
import werkzeug.wrappers
import werkzeug.serving

import odoo
from odoo.tools import config

_logger = logging.getLogger(__name__)

# XML-RPC fault codes. Some care must be taken when changing these: the
# constants are also defined client-side and must remain in sync.
# User code must use the exceptions defined in ``odoo.exceptions`` (not
# create directly ``xmlrpclib.Fault`` objects).
RPC_FAULT_CODE_CLIENT_ERROR = 1 # indistinguishable from app. error.
RPC_FAULT_CODE_APPLICATION_ERROR = 1
RPC_FAULT_CODE_WARNING = 2
RPC_FAULT_CODE_ACCESS_DENIED = 3
RPC_FAULT_CODE_ACCESS_ERROR = 4

def xmlrpc_handle_exception_int(e):
    if isinstance(e, odoo.exceptions.RedirectWarning):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_WARNING, str(e))
    elif isinstance(e, odoo.exceptions.AccessError):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_ACCESS_ERROR, str(e))
    elif isinstance(e, odoo.exceptions.AccessDenied):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_ACCESS_DENIED, str(e))
    elif isinstance(e, odoo.exceptions.UserError):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_WARNING, str(e))
    else:
        info = sys.exc_info()
        # Which one is the best ?
        formatted_info = "".join(traceback.format_exception(*info))
        #formatted_info = odoo.tools.exception_to_unicode(e) + '\n' + info
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_APPLICATION_ERROR, formatted_info)

    return xmlrpclib.dumps(fault, allow_none=None)

def xmlrpc_handle_exception_string(e):
    if isinstance(e, odoo.exceptions.RedirectWarning):
        fault = xmlrpclib.Fault('warning -- Warning\n\n' + str(e), '')
    elif isinstance(e, odoo.exceptions.MissingError):
        fault = xmlrpclib.Fault('warning -- MissingError\n\n' + str(e), '')
    elif isinstance(e, odoo.exceptions.AccessError):
        fault = xmlrpclib.Fault('warning -- AccessError\n\n' + str(e), '')
    elif isinstance(e, odoo.exceptions.AccessDenied):
        fault = xmlrpclib.Fault('AccessDenied', str(e))
    elif isinstance(e, odoo.exceptions.UserError):
        fault = xmlrpclib.Fault('warning -- UserError\n\n' + str(e), '')
    #InternalError
    else:
        info = sys.exc_info()
        formatted_info = "".join(traceback.format_exception(*info))
        fault = xmlrpclib.Fault(odoo.tools.exception_to_unicode(e), formatted_info)

    return xmlrpclib.dumps(fault, allow_none=None, encoding=None)

def _patch_xmlrpc_marshaller():
    # By default, in xmlrpc, bytes are converted to xmlrpclib.Binary object.
    # Historically, odoo is sending binary as base64 string.
    # In python 3, base64.b64{de,en}code() methods now works on bytes.
    # Convert them to str to have a consistent behavior between python 2 and python 3.
    # TODO? Create a `/xmlrpc/3` route prefix that respect the standard and uses xmlrpclib.Binary.
    def dump_bytes(marshaller, value, write):
        marshaller.dump_unicode(odoo.tools.ustr(value), write)

    xmlrpclib.Marshaller.dispatch[bytes] = dump_bytes

application = app = http.OdooApplication()
