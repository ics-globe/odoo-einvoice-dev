# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
import functools
import itertools
import logging
import psycopg2
import datetime

from odoo import api, fields, models
from odoo import SUPERUSER_ID, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import mute_logger

_logger = logging.getLogger('base.partner.merge')

class MergePartnerLine(models.TransientModel):

    _name = 'base.partner.merge.line'
    _description = 'Merge Partner Line'
    _order = 'min_id asc'

    wizard_id = fields.Many2one('base.partner.merge.automatic.wizard', 'Wizard')
    min_id = fields.Integer('MinID')
    aggr_ids = fields.Char('Ids', required=True)


class MergePartnerAutomatic(models.TransientModel):
    """
        The idea behind this wizard is to create a list of potential partners to
        merge. We use two objects, the first one is the wizard for the end-user.
        And the second will contain the partner list to merge.
    """

    _name = 'base.partner.merge.automatic.wizard'
    _description = 'Merge Partner Wizard'

    @api.model
    def default_get(self, fields):
        res = super(MergePartnerAutomatic, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if self.env.context.get('active_model') == 'res.partner' and active_ids:
            res['state'] = 'selection'
            res['partner_ids'] = [(6, 0, active_ids)]
            res['dst_partner_id'] = self._get_ordered_partner(active_ids)[-1].id
        return res

    # Group by
    group_by_email = fields.Boolean('Email')
    group_by_name = fields.Boolean('Name')
    group_by_is_company = fields.Boolean('Is Company')
    group_by_vat = fields.Boolean('VAT')
    group_by_parent_id = fields.Boolean('Parent Company')

    state = fields.Selection([
        ('option', 'Option'),
        ('selection', 'Selection'),
        ('finished', 'Finished')
    ], readonly=True, required=True, string='State', default='option')

    number_group = fields.Integer('Group of Contacts', readonly=True)
    current_line_id = fields.Many2one('base.partner.merge.line', string='Current Line')
    line_ids = fields.One2many('base.partner.merge.line', 'wizard_id', string='Lines')
    partner_ids = fields.Many2many('res.partner', string='Contacts')
    dst_partner_id = fields.Many2one('res.partner', string='Destination Contact')

    exclude_contact = fields.Boolean('A user associated to the contact')
    exclude_journal_item = fields.Boolean('Journal Items associated to the contact')
    maximum_group = fields.Integer('Maximum of Group of Contacts')

    # ----------------------------------------
    # Update method. Core methods to merge steps
    # ----------------------------------------

    def _merge(self, partner_ids, dst_partner=None, extra_checks=True):
        """ private implementation of merge partner
            :param partner_ids : ids of partner to merge
            :param dst_partner : record of destination res.partner
            :param extra_checks: pass False to bypass extra sanity check (e.g. email address)
        """
        # super-admin can be used to bypass extra checks
        if self.env.is_admin():
            extra_checks = False

        Partner = self.env['res.partner']
        partner_ids = Partner.browse(partner_ids).exists()
        if len(partner_ids) < 2:
            return

        if len(partner_ids) > 3:
            raise UserError(_("For safety reasons, you cannot merge more than 3 contacts together. You can re-open the wizard several times if needed."))

        # check if the list of partners to merge contains child/parent relation
        child_ids = self.env['res.partner']
        for partner_id in partner_ids:
            child_ids |= Partner.search([('id', 'child_of', [partner_id.id])]) - partner_id
        if partner_ids & child_ids:
            raise UserError(_("You cannot merge a contact with one of his parent."))

        if extra_checks and len(set(partner.email for partner in partner_ids)) > 1:
            raise UserError(_("All contacts must have the same email. Only the Administrator can merge contacts with different emails."))

        # remove dst_partner from partners to merge
        if dst_partner and dst_partner in partner_ids:
            src_partners = partner_ids - dst_partner
        else:
            ordered_partners = self._get_ordered_partner(partner_ids.ids)
            dst_partner = ordered_partners[-1]
            src_partners = ordered_partners[:-1]
        _logger.info("dst_partner: %s", dst_partner.id)

        # FIXME: is it still required to make and exception for account.move.line since accounting v9.0 ?
        if extra_checks and 'account.move.line' in self.env and self.env['account.move.line'].sudo().search([('partner_id', 'in', [partner.id for partner in src_partners])]):
            raise UserError(_("Only the destination contact may be linked to existing Journal Items. Please ask the Administrator if you need to merge several contacts linked to existing Journal Items."))

        # Make the company of all related users consistent with destination partner company
        if dst_partner.company_id:
            partner_ids.mapped('user_ids').sudo().write({
                'company_ids': [(4, dst_partner.company_id.id)],
                'company_id': dst_partner.company_id.id
            })

        # call sub methods to do the merge
        dst_partner.merge_records(src_partners, ignore_table='base_partner_merge')
        self.invalidate_cache()

    # ----------------------------------------
    # Helpers
    # ----------------------------------------

    @api.model
    def _generate_query(self, fields, maximum_group=100):
        """ Build the SQL query on res.partner table to group them according to given criteria
            :param fields : list of column names to group by the partners
            :param maximum_group : limit of the query
        """
        # make the list of column to group by in sql query
        sql_fields = []
        for field in fields:
            if field in ['email', 'name']:
                sql_fields.append('lower(%s)' % field)
            elif field in ['vat']:
                sql_fields.append("replace(%s, ' ', '')" % field)
            else:
                sql_fields.append(field)
        group_fields = ', '.join(sql_fields)

        # where clause : for given group by columns, only keep the 'not null' record
        filters = []
        for field in fields:
            if field in ['email', 'name', 'vat']:
                filters.append((field, 'IS NOT', 'NULL'))
        criteria = ' AND '.join('%s %s %s' % (field, operator, value) for field, operator, value in filters)

        # build the query
        text = [
            "SELECT min(id), array_agg(id)",
            "FROM res_partner",
        ]

        if criteria:
            text.append('WHERE %s' % criteria)

        text.extend([
            "GROUP BY %s" % group_fields,
            "HAVING COUNT(*) >= 2",
            "ORDER BY min(id)",
        ])

        if maximum_group:
            text.append("LIMIT %s" % maximum_group,)

        return ' '.join(text)

    @api.model
    def _compute_selected_groupby(self):
        """ Returns the list of field names the partner can be grouped (as merge
            criteria) according to the option checked on the wizard
        """
        groups = []
        group_by_prefix = 'group_by_'

        for field_name in self._fields:
            if field_name.startswith(group_by_prefix):
                if getattr(self, field_name, False):
                    groups.append(field_name[len(group_by_prefix):])

        if not groups:
            raise UserError(_("You have to specify a filter for your selection."))

        return groups

    @api.model
    def _partner_use_in(self, aggr_ids, models):
        """ Check if there is no occurence of this group of partner in the selected model
            :param aggr_ids : stringified list of partner ids separated with a comma (sql array_agg)
            :param models : dict mapping a model name with its foreign key with res_partner table
        """
        return any(
            self.env[model].search_count([(field, 'in', aggr_ids)])
            for model, field in models.items()
        )

    @api.model
    def _get_ordered_partner(self, partner_ids):
        """ Helper : returns a `res.partner` recordset ordered by create_date/active fields
            :param partner_ids : list of partner ids to sort
        """
        return self.env['res.partner'].browse(partner_ids).sorted(
            key=lambda p: (p.active, (p.create_date or datetime.datetime(1970, 1, 1))),
            reverse=True,
        )

    def _compute_models(self):
        """ Compute the different models needed by the system if you want to exclude some partners. """
        model_mapping = {}
        if self.exclude_contact:
            model_mapping['res.users'] = 'partner_id'
        if 'account.move.line' in self.env and self.exclude_journal_item:
            model_mapping['account.move.line'] = 'partner_id'
        return model_mapping

    # ----------------------------------------
    # Actions
    # ----------------------------------------

    def action_skip(self):
        """ Skip this wizard line. Don't compute any thing, and simply redirect to the new step."""
        if self.current_line_id:
            self.current_line_id.unlink()
        return self._action_next_screen()

    def _action_next_screen(self):
        """ return the action of the next screen ; this means the wizard is set to treat the
            next wizard line. Each line is a subset of partner that can be merged together.
            If no line left, the end screen will be displayed (but an action is still returned).
        """
        values = {}
        if self.line_ids:
            # in this case, we try to find the next record.
            current_line = self.line_ids[0]
            current_partner_ids = literal_eval(current_line.aggr_ids)
            values.update({
                'current_line_id': current_line.id,
                'partner_ids': [(6, 0, current_partner_ids)],
                'dst_partner_id': self._get_ordered_partner(current_partner_ids)[-1].id,
                'state': 'selection',
            })
        else:
            values.update({
                'current_line_id': False,
                'partner_ids': [],
                'state': 'finished',
            })

        self.write(values)

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _process_query(self, query):
        """ Execute the select request and write the result in this wizard
            :param query : the SQL query used to fill the wizard line
        """
        self.ensure_one()
        model_mapping = self._compute_models()

        # group partner query
        self._cr.execute(query)

        counter = 0
        for min_id, aggr_ids in self._cr.fetchall():
            # To ensure that the used partners are accessible by the user
            partners = self.env['res.partner'].search([('id', 'in', aggr_ids)])
            if len(partners) < 2:
                continue

            # exclude partner according to options
            if model_mapping and self._partner_use_in(partners.ids, model_mapping):
                continue

            self.env['base.partner.merge.line'].create({
                'wizard_id': self.id,
                'min_id': min_id,
                'aggr_ids': partners.ids,
            })
            counter += 1

        self.write({
            'state': 'selection',
            'number_group': counter,
        })

        _logger.info("counter: %s", counter)

    def action_start_manual_process(self):
        """ Start the process 'Merge with Manual Check'. Fill the wizard according to the group_by and exclude
            options, and redirect to the first step (treatment of first wizard line). After, for each subset of
            partner to merge, the wizard will be actualized.
                - Compute the selected groups (with duplication)
                - If the user has selected the 'exclude_xxx' fields, avoid the partners
        """
        self.ensure_one()
        groups = self._compute_selected_groupby()
        query = self._generate_query(groups, self.maximum_group)
        self._process_query(query)
        return self._action_next_screen()

    def action_start_automatic_process(self):
        """ Start the process 'Merge Automatically'. This will fill the wizard with the same mechanism as 'Merge
            with Manual Check', but instead of refreshing wizard with the current line, it will automatically process
            all lines by merging partner grouped according to the checked options.
        """
        self.ensure_one()
        self.action_start_manual_process()  # here we don't redirect to the next screen, since it is automatic process
        self.invalidate_cache() # FIXME: is this still necessary?

        for line in self.line_ids:
            partner_ids = literal_eval(line.aggr_ids)
            self._merge(partner_ids)
            line.unlink()
            self._cr.commit()  # TODO JEM : explain why

        self.write({'state': 'finished'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def parent_migration_process_cb(self):
        self.ensure_one()

        query = """
            SELECT
                min(p1.id),
                array_agg(DISTINCT p1.id)
            FROM
                res_partner as p1
            INNER join
                res_partner as p2
            ON
                p1.email = p2.email AND
                p1.name = p2.name AND
                (p1.parent_id = p2.id OR p1.id = p2.parent_id)
            WHERE
                p2.id IS NOT NULL
            GROUP BY
                p1.email,
                p1.name,
                CASE WHEN p1.parent_id = p2.id THEN p2.id
                    ELSE p1.id
                END
            HAVING COUNT(*) >= 2
            ORDER BY
                min(p1.id)
        """

        self._process_query(query)

        for line in self.line_ids:
            partner_ids = literal_eval(line.aggr_ids)
            self._merge(partner_ids)
            line.unlink()
            self._cr.commit()

        self.write({'state': 'finished'})

        self._cr.execute("""
            UPDATE
                res_partner
            SET
                is_company = NULL,
                parent_id = NULL
            WHERE
                parent_id = id
        """)

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_update_all_process(self):
        self.ensure_one()
        self.parent_migration_process_cb()

        # NOTE JEM : seems louche to create a new wizard instead of reuse the current one with updated options.
        # since it is like this from the initial commit of this wizard, I don't change it. yet ...
        wizard = self.create({'group_by_vat': True, 'group_by_email': True, 'group_by_name': True})
        wizard.action_start_automatic_process()

        # NOTE JEM : no idea if this query is usefull
        self._cr.execute("""
            UPDATE
                res_partner
            SET
                is_company = NULL
            WHERE
                parent_id IS NOT NULL AND
                is_company IS NOT NULL
        """)

        return self._action_next_screen()

    def action_merge(self):
        """ Merge Contact button. Merge the selected partners, and redirect to
            the end screen (since there is no other wizard line to process.
        """
        if not self.partner_ids:
            self.write({'state': 'finished'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        self._merge(self.partner_ids.ids, self.dst_partner_id)

        if self.current_line_id:
            self.current_line_id.unlink()

        return self._action_next_screen()
