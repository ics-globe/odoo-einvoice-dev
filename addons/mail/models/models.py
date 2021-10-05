# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml.builder import E

from odoo import api, models, tools, _


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def _valid_field_parameter(self, field, name):
        # allow tracking on abstract models; see also 'mail.thread'
        return (
            name == 'tracking' and self._abstract
            or super()._valid_field_parameter(field, name)
        )

    # ------------------------------------------------------------
    # GENERIC MAIL FEATURES
    # ------------------------------------------------------------

    def _mail_get_company_field(self):
        return 'company_id' if 'company_id' in self else False

    def _mail_get_companies(self, default=None):
        company_field = self._mail_get_company_field()
        if company_field:
            return self.env['res.company'].concat(*(record[company_field] for record in self))
        return self.env['res.company'].concat(
            *(default if default is not None else self.env.company
              for record in self)
        )

    def _mail_track(self, tracked_fields, initial):
        """ For a given record, fields to check (tuple column name, column info)
        and initial values, return a valid command to create tracking values.

        :param tracked_fields: fields_get of updated fields on which tracking
          is checked and performed;
        :param initial: dict of initial values for each updated fields;

        :return: a tuple (changes, tracking_value_ids) where
          changes: set of updated column names;
          tracking_value_ids: a list of ORM (0, 0, values) commands to create
          ``mail.tracking.value`` records;

        Override this method on a specific model to implement model-specific
        behavior. Also consider inheriting from ``mail.thread``. """
        self.ensure_one()
        changes = set()  # contains onchange tracked fields that changed
        tracking_value_ids = []

        # generate tracked_values data structure: {'col_name': {col_info, new_value, old_value}}
        for col_name, col_info in tracked_fields.items():
            if col_name not in initial:
                continue
            initial_value = initial[col_name]
            new_value = self[col_name]

            if new_value != initial_value and (new_value or initial_value):  # because browse null != False
                tracking_sequence = getattr(self._fields[col_name], 'tracking',
                                            getattr(self._fields[col_name], 'track_sequence', 100))  # backward compatibility with old parameter name
                if tracking_sequence is True:
                    tracking_sequence = 100
                tracking = self.env['mail.tracking.value'].create_tracking_values(initial_value, new_value, col_name, col_info, tracking_sequence, self._name)
                if tracking:
                    if tracking['field_type'] == 'monetary':
                        tracking['currency_id'] = getattr(self, col_info.get('currency_field', ''), self.company_id.currency_id).id
                    tracking_value_ids.append([0, 0, tracking])
                changes.add(col_name)

        return changes, tracking_value_ids

    def _message_get_default_recipients(self):
        """ Generic implementation for finding default recipient to mail on
        a recordset. This method is a generic implementation available for
        all models as we could send an email through mail templates on models
        not inheriting from mail.thread.

        Override this method on a specific model to implement model-specific
        behavior. Also consider inheriting from ``mail.thread``. """
        res = {}
        for record in self:
            recipient_ids, email_to, email_cc = [], False, False
            if 'partner_id' in record and record.partner_id:
                recipient_ids.append(record.partner_id.id)
            elif 'email_normalized' in record and record.email_normalized:
                email_to = record.email_normalized
            elif 'email_from' in record and record.email_from:
                email_to = record.email_from
            elif 'partner_email' in record and record.partner_email:
                email_to = record.partner_email
            elif 'email' in record and record.email:
                email_to = record.email
            res[record.id] = {'partner_ids': recipient_ids, 'email_to': email_to, 'email_cc': email_cc}
        return res

    def _notify_get_reply_to(self, default=None):
        """ Returns the preferred reply-to email address when replying to a thread
        on documents. This method is a generic implementation available for
        all models as we could send an email through mail templates on models
        not inheriting from mail.thread.

        Reply-to is formatted like "MyCompany MyDocument <reply.to@domain>".
        Heuristic it the following:
         * search for specific aliases as they always have priority; it is limited
           to aliases linked to documents (like project alias for task for example);
         * use catchall address;
         * use default;

        This method can be used as a generic tools if self is a void recordset.

        Override this method on a specific model to implement model-specific
        behavior. Also consider inheriting from ``mail.thread``.
        An example would be tasks taking their reply-to alias from their project.

        :param default: default email if no alias or catchall is found;
        :return result: dictionary. Keys are record IDs and value is formatted
          like an email "Company_name Document_name <reply_to@email>"/
        """
        _records = self
        model = _records._name if _records and _records._name != 'mail.thread' else False
        res_ids = _records.ids if _records and model else []
        _res_ids = res_ids or [False]  # always have a default value located in False

        # group ids per company
        _records_sudo = _records.sudo()
        company_to_res_ids = dict()
        if res_ids:
            for record in _records_sudo:
                record_company = record._mail_get_companies()
                company_to_res_ids.setdefault(record_company, list())
                company_to_res_ids[record_company] += record.ids
        else:
            company_to_res_ids[self.env.company] = _res_ids

        reply_to_formatted = dict.fromkeys(_res_ids, False)
        doc_names = dict()
        if model and res_ids:
            doc_names = dict(
                (record.id, record.display_name)
                for record in _records_sudo
            )

        for company, record_ids in company_to_res_ids.items():
            reply_to_email = dict()
            alias_domain = company.alias_domain_id
            if not alias_domain:
                continue

            if model and record_ids:
                mail_aliases = self.env['mail.alias'].sudo().search([
                    ('alias_parent_model_id.model', '=', model),
                    ('alias_parent_thread_id', 'in', record_ids),
                    ('alias_name', '!=', False)])
                # take only first found alias for each thread_id, to match order (1 found -> limit=1 for each res_id)
                for alias in mail_aliases:
                    reply_to_email.setdefault(
                        alias.alias_parent_thread_id,
                        '%s@%s' % (alias.alias_name, alias_domain.name)
                    )

            # left ids: use catchall defined on alias domain
            left_ids = set(record_ids) - set(reply_to_email)
            if left_ids:
                reply_to_email.update(
                    dict((rid, company.catchall_email) for rid in left_ids)
                )

            # compute name of reply-to ("Company Document" <alias@domain>)
            for res_id in reply_to_email:
                if doc_names.get(res_id):
                    name = '%s %s' % (company.name, doc_names[res_id])
                else:
                    name = company.name
                reply_to_formatted[res_id] = tools.formataddr((name, reply_to_email[res_id]))

        left_ids = set(_res_ids) - set(res_id for res_id, value in reply_to_formatted.items() if value)
        if left_ids:
            reply_to_formatted.update(dict((res_id, default) for res_id in left_ids))

        return reply_to_formatted

    # ------------------------------------------------------------
    # ALIAS MANAGEMENT
    # ------------------------------------------------------------

    def _alias_get_bounce_alias(self):
        return self.env['ir.config_parameter'].sudo().get_param('mail.bounce.alias')

    def _alias_get_bounce_email(self):
        bounce_alias = self._alias_get_bounce_alias()
        catchall_domain = self._alias_get_domain()
        if bounce_alias and catchall_domain:
            return '%s@%s' % (bounce_alias, catchall_domain)
        return False

    def _alias_get_catchall_alias(self):
        return self.env['ir.config_parameter'].sudo().get_param('mail.catchall.alias')

    def _alias_get_catchall_email(self):
        catchall_alias = self._alias_get_catchall_alias()
        catchall_domain = self._alias_get_domain()
        if catchall_alias and catchall_domain:
            return '%s@%s' % (catchall_alias, catchall_domain)
        return False

    def _alias_get_domain(self):
        # return self._alias_get_domains()[0]
        return self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")

    def _alias_get_domain_names(self):
        return [
            company.alias_domain_id.name
            for company in self._mail_get_companies()
        ]

    def _alias_get_error_message(self, message, message_dict, alias):
        """ Generic method that takes a record not necessarily inheriting from
        mail.alias.mixin. """
        author = self.env['res.partner'].browse(message_dict.get('author_id', False))
        if alias.alias_contact == 'followers':
            if not self.ids:
                return _('incorrectly configured alias (unknown reference record)')
            if not hasattr(self, "message_partner_ids"):
                return _('incorrectly configured alias')
            if not author or author not in self.message_partner_ids:
                return _('restricted to followers')
        elif alias.alias_contact == 'partners' and not author:
            return _('restricted to known authors')
        return False

    # ------------------------------------------------------------
    # ACTIVITY
    # ------------------------------------------------------------

    @api.model
    def _get_default_activity_view(self):
        """ Generates an empty activity view.

        :returns: a activity view as an lxml document
        :rtype: etree._Element
        """
        field = E.field(name=self._rec_name_fallback())
        activity_box = E.div(field, {'t-name': "activity-box"})
        templates = E.templates(activity_box)
        return E.activity(templates, string=self._description)

    # ------------------------------------------------------------
    # GATEWAY: NOTIFICATION
    # ------------------------------------------------------------

    def _mail_get_message_subtypes(self):
        return self.env['mail.message.subtype'].search([
            '&', ('hidden', '=', False),
            '|', ('res_model', '=', self._name), ('res_model', '=', False)])

    def _notify_by_email_get_headers(self):
        """
            Generate the email headers based on record
        """
        if not self:
            return {}
        self.ensure_one()
        return repr(self._notify_by_email_get_headers_dict())

    def _notify_by_email_get_headers_dict(self):
        return {
            'X-Odoo-Objects': "%s-%s" % (self._name, self.id),
        }
