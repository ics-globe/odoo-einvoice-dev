# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging


from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResUsersDeletion(models.Model):
    """User deletion requests.

    Those requests are logged in a different model to keep a trace of this action and the
    deletion is done in a CRON. Indeed, removing a user can be a heavy operation on
    large database (because of create_uid, write_uid on each model, which are not always
    indexed).
    """
    _name = 'res.users.deletion'
    _description = 'Users Deletion Request'

    # Integer field because the related user might be deleted from the database
    user_id = fields.Integer('User Id', required=True)

    state = fields.Selection([('todo', 'To Do'), ('done', 'Done'), ('fail', 'Failed')], required=True, string='State')

    @api.autovacuum
    def _gc_portal_users(self):
        """Remove the portal users that asked to deactivate their account.

        (see <res.users>::_deactivate_portal_user)

        Removing a user can be an heavy operation on large database (because of
        create_uid, write_uid on each models, which are not always indexed). Because of
        that, this operation is done in a CRON.
        """
        delete_requests = self.search([('state', '=', 'todo')])

        for delete_request in delete_requests:
            user = self.env['res.users'].browse(delete_request.user_id).exists()
            if not user:
                # user has already been deleted
                delete_request.state = 'done'
                continue

            try:
                with self.env.cr.savepoint():
                    partner = user.partner_id
                    user.unlink()
                    partner.unlink()
                    _logger.info('User #%i deleted', user.id)
                    delete_request.state = 'done'
            except Exception:
                delete_request.state = 'fail'
