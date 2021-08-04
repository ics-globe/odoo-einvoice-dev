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
#@check
def execute(db, uid, obj, method, *args, **kw):
    threading.currentThread().dbname = db
    with odoo.registry(db).cursor() as cr:
        check_method_name(method)
        res = execute_cr(cr, uid, obj, method, *args, **kw)
        if res is None:
            _logger.info('The method %s of the object %s can not return `None` !', method, obj)
        return res


def retrying(endpoint, **params):
    env = odoo.http.request.env

    def as_validation_error(exc):
        """ Return the IntegrityError encapsuled in a nice ValidationError """
        unknown = _('Unknown')
        for name, rclass in env.registry.items():
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

        if exc.diag.constraint_name in env.registry._sql_constraints:
            return ValidationError(_(CONSTRAINT_VIOLATION_MESSAGE,
                translate_sql_constraint(exc.diag.constraint_name, self.env.cr, self.env.context['lang'])
            ))

        return ValidationError(_(INTEGRITY_ERROR_MESSAGE, exc.args[0]))

    try:
        for tryno in range(1, MAX_TRIES_ON_CONCURRENCY_FAILURE + 1):
            tryleft = MAX_TRIES_ON_CONCURRENCY_FAILURE - tryno
            try:
                result = endpoint(**params)
                if not env.cr._closed:
                    env.cr._precommit()
                    env.cr._commit()
                return result
            except (IntegrityError, OperationalError) as exc:
                if env.cr._closed:
                    raise
                env.cr.rollback()
                env.registry.reset_changes()
                env.clear()
                request.reload_session()
                if type(exc) is IntegrityError:
                    raise as_validation_error(exc) from exc
                if e.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY:
                    raise
                if not tryleft:
                    _logger.info("%s, maximum number of tries reached!", errorcodes.lookup(e.pgcode))
                    raise

            wait_time = random.uniform(0.0, 2 ** tryno)
            _logger.info("%s, %s tries left, try again in %.04f sec...", errorcodes.lookup(e.pgcode), tryleft, wait_time)
            time.sleep(wait_time)

        raise RuntimeError("unreachable")
    except Exception:
        env.registry.reset_changes()
        raise
    else:
        if not env.cr._closed:
            env.cr._postcommit()
        env.registry.signal_changes()
