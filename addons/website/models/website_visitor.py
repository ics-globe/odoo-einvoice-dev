# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import hashlib
import pytz

from odoo import fields, models, api, _
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import UserError
from odoo.tools.misc import _format_time_ago
from odoo.http import request
from odoo.osv import expression


class WebsiteTrack(models.Model):
    _name = 'website.track'
    _description = 'Visited Pages'
    _order = 'visit_datetime DESC'
    _log_access = False

    visitor_id = fields.Many2one('website.visitor', ondelete="cascade", index=True, required=True, readonly=True)
    page_id = fields.Many2one('website.page', index=True, ondelete='cascade', readonly=True)
    url = fields.Text('Url', index=True)
    visit_datetime = fields.Datetime('Visit Date', default=fields.Datetime.now, required=True, readonly=True)


class WebsiteVisitor(models.Model):
    _name = 'website.visitor'
    _description = 'Website Visitor'
    _order = 'id DESC'

    def _get_access_token(self):
        """ Either the user's partner.id or a hash. """
        assert request, _("Visitors can only be created through the frontend.")

        if not self.env.user._is_public():
            return self.env.user.partner_id.id

        msg = repr((
            request.httprequest.remote_addr,
            request.httprequest.environ.get('HTTP_USER_AGENT'),
            fields.Date.today().strftime('%Y-%m'),
            self.env["ir.config_parameter"].sudo().get_param("database.secret"),
            # For testing purpose, uncomment this line if you want different
            # URL (domain/ip) to generate different visitor.
            # request.httprequest.host,
        )).encode('utf-8')
        return hashlib.sha1(msg).hexdigest()

    name = fields.Char('Name', related='partner_id.name')
    access_token = fields.Char(required=True, default=_get_access_token, copy=False)
    website_id = fields.Many2one('website', "Website", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Contact", help="Partner of the last logged in user.", compute='_compute_partner_id', store=True, index='btree_not_null')
    partner_image = fields.Binary(related='partner_id.image_1920')

    # localisation and info
    country_id = fields.Many2one('res.country', 'Country', readonly=True)
    country_flag = fields.Char(related="country_id.image_url", string="Country Flag")
    lang_id = fields.Many2one('res.lang', string='Language', help="Language from the website when visitor has been created")
    timezone = fields.Selection(_tz_get, string='Timezone')
    email = fields.Char(string='Email', compute='_compute_email_phone')
    mobile = fields.Char(string='Mobile', compute='_compute_email_phone')

    # Visit fields
    visit_count = fields.Integer('# Visits', default=1, readonly=True, help="A new visit is considered if last connection was more than 8 hours ago.")
    website_track_ids = fields.One2many('website.track', 'visitor_id', string='Visited Pages History', readonly=True)
    visitor_page_count = fields.Integer('Page Views', compute="_compute_page_statistics", help="Total number of visits on tracked pages")
    page_ids = fields.Many2many('website.page', string="Visited Pages", compute="_compute_page_statistics", groups="website.group_website_designer")
    page_count = fields.Integer('# Visited Pages', compute="_compute_page_statistics", help="Total number of tracked page visited")
    last_visited_page_id = fields.Many2one('website.page', string="Last Visited Page", compute="_compute_last_visited_page_id")

    # Time fields
    create_date = fields.Datetime('First Connection', readonly=True)
    last_connection_datetime = fields.Datetime('Last Connection', default=fields.Datetime.now, help="Last page view date", readonly=True)
    time_since_last_action = fields.Char('Last action', compute="_compute_time_statistics", help='Time since last page view. E.g.: 2 minutes ago')
    is_connected = fields.Boolean('Is connected ?', compute='_compute_time_statistics', help='A visitor is considered as connected if his last page view was within the last 5 minutes.')

    _sql_constraints = [
        ('access_token_unique', 'unique(access_token)', 'Access token should be unique.'),
    ]

    @api.depends('partner_id')
    def name_get(self):
        res = []
        for record in self:
            res.append((
                record.id,
                record.partner_id.name or _('Website Visitor #%s', record.id)
            ))
        return res

    @api.depends('access_token')
    def _compute_partner_id(self):
        # The browse in the loop is fine, there is no SQL Query on partner here
        for visitor in self:
            visitor.partner_id = len(visitor.access_token) != 40 and self.env['res.partner'].browse([visitor.access_token])

    @api.depends('partner_id.email_normalized', 'partner_id.mobile', 'partner_id.phone')
    def _compute_email_phone(self):
        results = self.env['res.partner'].search_read(
            [('id', 'in', self.partner_id.ids)],
            ['id', 'email_normalized', 'mobile', 'phone'],
        )
        mapped_data = {
            result['id']: {
                'email_normalized': result['email_normalized'],
                'mobile': result['mobile'] if result['mobile'] else result['phone']
            } for result in results
        }

        for visitor in self:
            visitor.email = mapped_data.get(visitor.partner_id.id, {}).get('email_normalized')
            visitor.mobile = mapped_data.get(visitor.partner_id.id, {}).get('mobile')

    @api.depends('website_track_ids')
    def _compute_page_statistics(self):
        results = self.env['website.track']._read_group(
            [('visitor_id', 'in', self.ids), ('url', '!=', False)], ['visitor_id', 'page_id', 'url'], ['visitor_id', 'page_id', 'url'], lazy=False)
        mapped_data = {}
        for result in results:
            visitor_info = mapped_data.get(result['visitor_id'][0], {'page_count': 0, 'visitor_page_count': 0, 'page_ids': set()})
            visitor_info['visitor_page_count'] += result['__count']
            visitor_info['page_count'] += 1
            if result['page_id']:
                visitor_info['page_ids'].add(result['page_id'][0])
            mapped_data[result['visitor_id'][0]] = visitor_info

        for visitor in self:
            visitor_info = mapped_data.get(visitor.id, {'page_count': 0, 'visitor_page_count': 0, 'page_ids': set()})
            visitor.page_ids = [(6, 0, visitor_info['page_ids'])]
            visitor.visitor_page_count = visitor_info['visitor_page_count']
            visitor.page_count = visitor_info['page_count']

    @api.depends('website_track_ids.page_id')
    def _compute_last_visited_page_id(self):
        results = self.env['website.track']._read_group(
            [('visitor_id', 'in', self.ids)],
            ['visitor_id', 'page_id', 'visit_datetime:max'],
            ['visitor_id', 'page_id'], lazy=False)
        mapped_data = {result['visitor_id'][0]: result['page_id'][0] for result in results if result['page_id']}
        for visitor in self:
            visitor.last_visited_page_id = mapped_data.get(visitor.id, False)

    @api.depends('last_connection_datetime')
    def _compute_time_statistics(self):
        for visitor in self:
            visitor.time_since_last_action = _format_time_ago(self.env, (datetime.now() - visitor.last_connection_datetime))
            visitor.is_connected = (datetime.now() - visitor.last_connection_datetime) < timedelta(minutes=5)

    def _check_for_message_composer(self):
        """ Purpose of this method is to actualize visitor model prior to
        contacting him. Used notably for inheritance purpose, when dealing with
        leads that could update the visitor model. """
        return bool(self.partner_id and self.partner_id.email)

    def _prepare_message_composer_context(self):
        return {
            'default_model': 'res.partner',
            'default_res_id': self.partner_id.id,
            'default_partner_ids': [self.partner_id.id],
        }

    def action_send_mail(self):
        self.ensure_one()
        if not self._check_for_message_composer():
            raise UserError(_("There are no contact and/or no email linked to this visitor."))
        visitor_composer_ctx = self._prepare_message_composer_context()
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        compose_ctx = dict(
            default_use_template=False,
            default_composition_mode='comment',
        )
        compose_ctx.update(**visitor_composer_ctx)
        return {
            'name': _('Contact Visitor'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': compose_ctx,
        }

    def _get_visitor_from_request(self, force_create=False, force_track=False):
        """ Return the visitor as sudo from the request if there is a
        visitor for that device-ip-date.

        When fetching visitor, now that duplicates are linked to a main visitor
        instead of unlinked, you may have more collisions issues with cookie
        being set (after a de-connection for example).

        The visitor associated to a partner in case of public user is not taken
        into account, it is considered as desynchronized cookie.
        In addition, we also discard if the visitor has a main visitor whose
        partner is set (aka wrong after logout partner). """

        # This function can be called in json with mobile app.
        # In case of mobile app, no uid is set on the jsonRequest env.
        # In case of multi db, _env is None on request, and request.env unbound.
        if not (request and request.env and request.env.uid):
            return None

        Visitor = self.env['website.visitor'].sudo()
        visitor = Visitor
        access_token = self._get_access_token()

        if force_create:
            # This will create or return existing one
            visitor_values = Visitor._get_visitor_create_values()
            if len(str(access_token)) != 40:
                visitor_values['partner_id'] = access_token
            visitor_columns = ', '.join(visitor_values.keys())
            visitor_template = ', '.join('%s' for _ in visitor_values)
            query = f"""
                INSERT INTO website_visitor ({visitor_columns})
                VALUES ({visitor_template})
                ON CONFLICT (access_token)
                DO UPDATE SET
                    last_connection_datetime='{visitor_values['last_connection_datetime']}',
                    visit_count = CASE WHEN website_visitor.last_connection_datetime < NOW() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
                                       THEN website_visitor.visit_count + 1
                                       ELSE website_visitor.visit_count
                                  END
                RETURNING id"""
            query_values = tuple(visitor_values.values())

            if force_track:
                track_values = force_track['values']
                track_values['visit_datetime'] = visitor_values['last_connection_datetime']
                track_columns = ', '.join(track_values.keys())
                track_template = ', '.join('%s' for _ in track_values)
                query = f"""
                    WITH visitor AS (
                        {query}, {track_template}::timestamp
                    )
                    INSERT INTO website_track (visitor_id, {track_columns})
                    SELECT * FROM visitor RETURNING visitor_id;
                """
                query_values += tuple(track_values.values())

            self.env.cr.execute(query, query_values)
            visitor_id = self.env.cr.fetchone()[0]
            visitor = Visitor.browse(visitor_id)
            visitor._post_create()
        else:
            visitor = Visitor.search([('access_token', '=', access_token)])

        if not force_create and visitor and not visitor.timezone:
            tz = self._get_visitor_timezone()
            if tz:
                visitor._update_visitor_timezone(tz)

        return visitor

    def _post_create(self):
        pass

    def _handle_webpage_dispatch(self, website_page):
        """ Create a website.visitor if the http request object is a tracked
        website.page or a tracked ir.ui.view.
        Since this method is only called on tracked elements, the
        last_connection_datetime might not be accurate as the visitor could have
        been visiting only untracked page during his last visit."""

        url = request.httprequest.url
        website_track_values = {'url': url}
        if website_page:
            website_track_values['page_id'] = website_page.id
            domain = [('page_id', '=', website_page.id)]
        else:
            domain = [('url', '=', url)]
        self._get_visitor_from_request(force_create=True, force_track={
            'domain': domain,
            'values': website_track_values
        })

    def _add_tracking(self, domain, website_track_values):
        """ Add the track and update the visitor"""
        domain = expression.AND([domain, [('visitor_id', '=', self.id)]])
        last_view = self.env['website.track'].sudo().search(domain, limit=1)
        if not last_view or last_view.visit_datetime < datetime.now() - timedelta(minutes=30):
            website_track_values['visitor_id'] = self.id
            self.env['website.track'].create(website_track_values)
        self._update_visitor_last_visit()

    def _get_visitor_create_values(self):
        """ Get default visitor create values. """
        country_code = request.geoip.get('country_code')
        country_id = request.env['res.country'].sudo().search([('code', '=', country_code)], limit=1).id if country_code else False
        vals = {
            'lang_id': request.lang.id,
            'country_id': country_id,
            'website_id': request.website.id,
        }

        tz = self._get_visitor_timezone()
        if tz:
            vals['timezone'] = tz

        # TODO: This can be removed and `_prepare_create_values()` called
        # directly instead of `_add_missing_default_values()` once the ORM will
        # use python instead of SQL to get current date. See #85078
        vals['create_uid'] = vals['write_uid'] = self.env.uid
        vals['create_date'] = vals['write_date'] = datetime.utcnow()

        # Add missing default values and convert to SQL format
        vals = self._add_missing_default_values(vals)
        vals = {k: self._fields[k].convert_to_column(v, self) for k, v in vals.items()}

        return vals

    def _merge_visitor(self, target):
        """ Merge an anonymous visitor data to a partner visitor then unlink
        that anonymous visitor.
        Purpose is to try to aggregate as much sub-records (tracked pages,
        leads, ...) as possible.
        It is especially useful to aggregate data from the same user on
        different devices.

        This method is meant to be overridden for other modules to merge their
        own anonymous visitor data to the partner visitor before unlink.

        This method is only called after the user logs in.

        :param target: main visitor, target of link process;
        """
        assert target.partner_id
        self.website_track_ids.visitor_id = target.id
        self.unlink()

    def _cron_unlink_old_visitors(self):
        """ Unlink inactive visitors (see '_inactive_visitors_domain' for
        details).

        Visitors were previously archived but we came to the conclusion that
        archived visitors have very little value and bloat the database for no
        reason. """

        self.env['website.visitor'].sudo().search(self._inactive_visitors_domain()).unlink()

    def _inactive_visitors_domain(self):
        """ This method defines the domain of visitors that can be cleaned. By
        default visitors not linked to any partner and not active for
        'website.visitor.live.days' days (default being 60) are considered as
        inactive.

        This method is meant to be overridden by sub-modules to further refine
        inactivity conditions. """

        delay_days = int(self.env['ir.config_parameter'].sudo().get_param('website.visitor.live.days', 60))
        deadline = datetime.now() - timedelta(days=delay_days)
        return [('last_connection_datetime', '<', deadline), ('partner_id', '=', False)]

    def _update_visitor_timezone(self, timezone):
        """ We need to do this part here to avoid concurrent updates error. """
        query = """
            UPDATE website_visitor
            SET timezone = %s
            WHERE id IN (
                SELECT id FROM website_visitor WHERE id = %s
                FOR NO KEY UPDATE SKIP LOCKED
            )
        """
        self.env.cr.execute(query, (timezone, self.id))

    def _update_visitor_last_visit(self):
        date_now = datetime.now()
        query = "UPDATE website_visitor SET "
        if self.last_connection_datetime < (date_now - timedelta(hours=8)):
            query += "visit_count = visit_count + 1,"
        query += """
            last_connection_datetime = %s
            WHERE id IN (
                SELECT id FROM website_visitor WHERE id = %s
                FOR NO KEY UPDATE SKIP LOCKED
            )
        """
        self.env.cr.execute(query, (date_now, self.id), log_exceptions=False)

    def _get_visitor_timezone(self):
        tz = request.httprequest.cookies.get('tz') if request else None
        if tz in pytz.all_timezones:
            return tz
        elif not self.env.user._is_public():
            return self.env.user.tz
        else:
            return None
