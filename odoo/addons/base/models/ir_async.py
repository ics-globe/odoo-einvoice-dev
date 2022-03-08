# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class IrAsync(models.Model):
    _name = 'ir.async'
    _description = "Job Queue"

    state = fields.Selection([('enqueued', 'Enqueued'), ('succeeded', 'Succeeded'), ('failed', 'Failed')])
    call_at = fields.Datetime()
    model_name = fields.Char()
    method_name = fields.Char()
    records_ids = fields.Text()
    args = fields.Text()
    kwargs = fields.Text()
    user_id = fields.Many2one('res.users', string='Scheduler User', ondelete='cascade', )
    context = fields.Text()
    is_super_user = fields.Boolean()

    def _call_soon(self, method, *args, **kwargs):
        """
        Schedule the ``method`` to be called with the given arguments as
        soon as possible by a background worker.
        """
        return self._call_at(fields.Datetime.now(), method, *args, **kwargs)

    def _call_at(self, when, method, *args, **kwargs):
        """
        Schedule the ``method`` to be called with the given arguments at
        ``when`` (best-effort) by a background worker.
        """
        records = getattr(method, '__self__', None)
        if not isinstance(records, models.BaseModel):
            raise TypeError("You can only create an async task on a recordset.")
        model = records.__class__

        task = self.sudo().create({
            'state': 'enqueued',
            'call_at': when,
            'model_name': model._name,
            'method_name': method.__name__,
            'records_ids': json.dumps(records._ids or []),
            'args': json.dumps(args),
            'kwargs': json.dumps(kwargs),
            'user_id': records.env.uid,
            'context': json.dumps(records.env.context),
            'is_super_user': records.env.su,
        })

        self.env.ref('base.process_async_tasks_job')._trigger(when)

        return task

    def _process_tasks(self):
        """
        Process all the scheduled tasks that are set to run now.

        This method is NOT multithread/multiworker safe and should ONLY
        be called in an environment that guarantees it is only called
        once at every given moment in time.
        """
        ready_tasks = self.search([
            ('state', '=', 'enqueued'),
            ('call_at', '<=', fields.Datetime.now()),
        ])

        for task in ready_tasks:
            context = json.loads(task.context)
            records_ids = json.loads(task.records_ids)
            args = json.loads(task.args)
            kwargs = json.loads(task.kwargs)

            env = api.Environment(self.env.cr, task.user_id.id, context, task.is_super_user)
            records = env[task.model_name].browse(records_ids)
            method = getattr(records, task.method_name)

            _logger.info("Starting task #%s %s.%s.", task.id, task.model_name, task.method_name)
            try:
                with self.env.cr.savepoint():
                    method(*args, **kwargs)
            except Exception as exc:
                task.state = 'failed'
                _logger.exception("Task #%d %s.%s failed", task.id, task.model_name, task.method_name)
            else:
                task.state = 'succeeded'
                _logger.info("Task #%d %s.%s succeeded", task.id, task.model_name, task.method_name)

    @api.autovacuum
    def _vacuum_async_tasks(self):
        self.search([('state', 'in', ('succeeded', 'failed'))]).unlink()
