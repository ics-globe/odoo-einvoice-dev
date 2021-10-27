# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from logging import getLogger

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = getLogger(__name__)


class MailAlias(models.Model):
    _inherit = 'mail.alias'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_expense_alias(self):
        expense_alias = self.env.ref('hr_expense.mail_alias_expense', raise_if_not_found=False)
        if not expense_alias:
            _logger.warning('Missing expense generic alias `mail_alias_expense`. You should probably create the data again.')
        else:
            if any(alias == expense_alias for alias in self):
                raise UserError(
                    _('You cannot remove the alias %(alias_name)s as it is used to configure the expense gateway. You should empty its value instead.',
                      alias_name=expense_alias.alias_name
                     )
                )
        return super(MailAlias, self)._unlink_except_expense_alias()
