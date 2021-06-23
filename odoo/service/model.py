# -*- coding: utf-8 -*-

from contextlib import closing
from functools import wraps
import logging
from psycopg2 import IntegrityError, OperationalError, errorcodes
import random
import threading
import time

import odoo
from odoo.exceptions import UserError, ValidationError
from odoo.models import check_method_name
from odoo.tools.translate import translate, translate_sql_constraint
from odoo.tools.translate import _

from . import security
from ..tools import traverse_containers, lazy

_logger = logging.getLogger(__name__)


# MOVE to controller RPC
def dispatch(method, params):
    (db, uid, passwd ) = params[0], int(params[1]), params[2]

    # set uid tracker - cleaned up at the WSGI
    # dispatching phase in odoo.http.application
    threading.current_thread().uid = uid

    params = params[3:]
    if method == 'obj_list':
        raise NameError("obj_list has been discontinued via RPC as of 6.0, please query ir.model directly!")
    if method not in ['execute', 'execute_kw']:
        raise NameError("Method not available %s" % method)
    security.check(db,uid,passwd)
    registry = odoo.registry(db).check_signaling()
    fn = globals()[method]
    with registry.manage_changes():
        res = fn(db, uid, *params)
    return res


# MOVE to controller RPC and registry
def execute_cr(cr, uid, obj, method, *args, **kw):
    odoo.api.Environment.reset()  # clean cache etc if we retry the same transaction
    recs = odoo.api.Environment(cr, uid, {}).get(obj)
    if recs is None:
        raise UserError(_("Object %s doesn't exist", obj))
    result = odoo.api.call_kw(recs, method, args, kw)
    # force evaluation of lazy values before the cursor is closed, as it would
    # error afterwards if the lazy isn't already evaluated (and cached)
    for l in traverse_containers(result, lazy):
        _0 = l._value
    return result


# MOVE to controller RPC
def execute_kw(db, uid, obj, method, args, kw=None):
    return execute(db, uid, obj, method, *args, **kw or {})

# MOVE to controller RPC
@check
def execute(db, uid, obj, method, *args, **kw):
    threading.currentThread().dbname = db
    with odoo.registry(db).cursor() as cr:
        check_method_name(method)
        res = execute_cr(cr, uid, obj, method, *args, **kw)
        if res is None:
            _logger.info('The method %s of the object %s can not return `None` !', method, obj)
        return res
