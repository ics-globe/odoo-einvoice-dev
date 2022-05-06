# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from lxml import objectify
from unittest.mock import patch
from werkzeug import urls

from odoo.fields import Command
from odoo.tests.common import TransactionCase
from odoo.tools.misc import hmac as hmac_tool

_logger = logging.getLogger(__name__)


class PaymentCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.currency_euro = cls._prepare_currency('EUR')
        cls.currency_usd = cls._prepare_currency('USD')

        cls.country_belgium = cls.env.ref('base.be')
        cls.country_france = cls.env.ref('base.fr')
        cls.europe = cls.env.ref('base.europe')

        cls.group_user = cls.env.ref('base.group_user')
        cls.group_portal = cls.env.ref('base.group_portal')
        cls.group_public = cls.env.ref('base.group_public')

        cls.admin_user = cls.env.ref('base.user_admin')
        cls.internal_user = cls.env['res.users'].create({
            'name': 'Internal User (Test)',
            'login': 'internal',
            'password': 'internal',
            'groups_id': [Command.link(cls.group_user.id)]
        })
        cls.portal_user = cls.env['res.users'].create({
            'name': 'Portal User (Test)',
            'login': 'payment_portal',
            'password': 'payment_portal',
            'groups_id': [Command.link(cls.group_portal.id)]
        })
        cls.public_user = cls.env.ref('base.public_user')

        cls.admin_partner = cls.admin_user.partner_id
        cls.internal_partner = cls.internal_user.partner_id
        cls.portal_partner = cls.portal_user.partner_id
        cls.default_partner = cls.env['res.partner'].create({
            'name': 'Norbert Buyer',
            'lang': 'en_US',
            'email': 'norbert.buyer@example.com',
            'street': 'Huge Street',
            'street2': '2/543',
            'phone': '0032 12 34 56 78',
            'city': 'Sin City',
            'zip': '1000',
            'country_id': cls.country_belgium.id,
        })

        # Create a dummy acquirer to allow basic tests without any specific acquirer implementation
        arch = """
        <form action="dummy" method="post">
            <input type="hidden" name="view_id" t-att-value="viewid"/>
            <input type="hidden" name="user_id" t-att-value="user_id.id"/>
        </form>
        """  # We exploit the default values `viewid` and `user_id` from QWeb's rendering context
        redirect_form = cls.env['ir.ui.view'].create({
            'name': "Dummy Redirect Form",
            'type': 'qweb',
            'arch': arch,
        })

        cls.dummy_acquirer = cls.env['payment.acquirer'].create({
            'name': "Dummy Acquirer",
            'provider': 'none',
            'state': 'test',
            'allow_tokenization': True,
            'redirect_form_view_id': redirect_form.id,
        })

        cls.acquirer = cls.dummy_acquirer
        cls.amount = 1111.11
        cls.company = cls.env.company
        cls.currency = cls.currency_euro
        cls.partner = cls.default_partner
        cls.reference = "Test Transaction"

        account_payment_module = cls.env['ir.module.module']._get('account_payment')
        cls.account_payment_installed = account_payment_module.state in ('installed', 'to upgrade')

    def setUp(self):
        # TODO make common in acc_pay disabling the patcher
        # and implement a removeCleanup ?
        super().setUp()
        if self.account_payment_installed:
            # disable account payment generation if account_payment is installed
            # because the accounting setup of acquirers is not managed in this common
            self.reconcile_after_done_patcher = patch(
                'odoo.addons.account_payment.models.payment_transaction.PaymentTransaction._reconcile_after_done',
            )
            self.reconcile_after_done_patcher.start()

    def tearDown(self):
        super().tearDown()
        # Magic hack: we start the patcher even if it was started already
        # so that we do not call stop on a non started patcher.
        self.reconcile_after_done_patcher.start()
        self.reconcile_after_done_patcher.stop()

    #=== Utils ===#

    @classmethod
    def _prepare_currency(cls, currency_code):
        currency = cls.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', currency_code.upper())]
        )
        currency.action_unarchive()
        return currency

    def _generate_test_access_token(self, *values):
        """ Generate an access token based on the provided values for testing purposes.

        This methods returns a token identical to that generated by
        payment.utils.generate_access_token but uses the test class environment rather than the
        environment of odoo.http.request.

        See payment.utils.generate_access_token for additional details.

        :param list values: The values to use for the generation of the token
        :return: The generated access token
        :rtype: str
        """
        token_str = '|'.join(str(val) for val in values)
        access_token = hmac_tool(self.env(su=True), 'generate_access_token', token_str)
        return access_token

    def _build_url(self, route):
        return urls.url_join(self.base_url(), route)

    def _extract_values_from_html_form(self, html_form):
        """ Extract the transaction rendering values from an HTML form.

        :param str html_form: The HTML form
        :return: The extracted information (action & inputs)
        :rtype: dict[str:str]
        """
        html_tree = objectify.fromstring(html_form)
        action = html_tree.get('action')
        inputs = {form_input.get('name'): form_input.get('value') for form_input in html_tree.input}
        return {
            'action': action,
            'inputs': inputs,
        }

    def _assert_does_not_raise(self, exception_class, func, *args, **kwargs):
        """ Fail if an exception of the provided class is raised when calling the function.

        If an exception of any other class is raised, it is caught and silently ignored.

        This method cannot be used with functions that make requests. Any exception raised in the
        scope of the new request will not be caught and will make the test fail.

        :param class exception_class: The class of the exception to monitor
        :param function fun: The function to call when monitoring for exceptions
        :param list args: The positional arguments passed as-is to the called function
        :param dict kwargs: The keyword arguments passed as-is to the called function
        :return: None
        """
        try:
            func(*args, **kwargs)
        except exception_class:
            self.fail(f"{func.__name__} should not raise error of class {exception_class.__name__}")
        except Exception:
            pass  # Any exception whose class is not monitored is caught and ignored

    @classmethod
    def _prepare_acquirer(cls, provider='none', company=None, update_values=None):
        """ Prepare and return the first acquirer matching the given provider and company.

        If no acquirer is found in the given company, we duplicate the one from the base company.

        All other acquirers belonging to the same company are disabled to avoid any interferences.

        :param str provider: The provider of the acquirer to prepare
        :param recordset company: The company of the acquirer to prepare, as a `res.company` record
        :param dict update_values: The values used to update the acquirer
        :return: The acquirer to prepare, if found
        :rtype: recordset of `payment.acquirer`
        """
        company = company or cls.env.company
        update_values = update_values or {}

        acquirer = cls.env['payment.acquirer'].sudo().search(
            [('provider', '=', provider), ('company_id', '=', company.id)], limit=1
        )
        if not acquirer:
            base_acquirer = cls.env['payment.acquirer'].sudo().search(
                [('provider', '=', provider)], limit=1
            )
            if not base_acquirer:
                _logger.error("no payment.acquirer found for provider %s", provider)
                return cls.env['payment.acquirer']
            else:
                acquirer = base_acquirer.copy({'company_id': company.id})

        update_values['state'] = 'test'
        acquirer.write(update_values)
        return acquirer

    def create_transaction(self, flow, sudo=True, **values):
        default_values = {
            'amount': self.amount,
            'currency_id': self.currency.id,
            'acquirer_id': self.acquirer.id,
            'reference': self.reference,
            'operation': f'online_{flow}',
            'partner_id': self.partner.id,
        }
        return self.env['payment.transaction'].sudo(sudo).create(dict(default_values, **values))

    def create_token(self, sudo=True, **values):
        default_values = {
            'name': "XXXXXXXXXXXXXXX-2565 (TEST)",
            'acquirer_id': self.acquirer.id,
            'partner_id': self.partner.id,
            'acquirer_ref': "Acquirer Ref (TEST)",
        }
        return self.env['payment.token'].sudo(sudo).create(dict(default_values, **values))

    def _get_tx(self, reference):
        return self.env['payment.transaction'].sudo().search([
            ('reference', '=', reference),
        ])

    def _prepare_transaction_values(self, payment_option_id, flow):
        """ Prepare the basic payment/transaction route values.

        :param int payment_option_id: The payment option handling the transaction, as a
                                      `payment.acquirer` id or a `payment.token` id
        :param str flow: The payment flow
        :return: The route values
        :rtype: dict
        """
        return {
            'amount': self.amount,
            'currency_id': self.currency.id,
            'partner_id': self.partner.id,
            'access_token': self._generate_test_access_token(
                self.partner.id, self.amount, self.currency.id
            ),
            'payment_option_id': payment_option_id,
            'reference_prefix': 'test',
            'tokenization_requested': True,
            'landing_route': 'Test',
            'is_validation': False,
            # FIXME VFE
            # 'invoice_id': self.invoice.id,
            'flow': flow,
        }
