# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.account.models.account_payment_method import AccountPaymentMethod
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.payment.tests.common import PaymentCommon


class AccountPaymentCommon(PaymentCommon, AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, *kw):
        # Do not forward the fucking annoying chart_template_ref compta binz
        super().setUpClass()

        Method_get_payment_method_information = AccountPaymentMethod._get_payment_method_information

        def _get_payment_method_information(self):
            res = Method_get_payment_method_information(self)
            res['none'] = {'mode': 'multi', 'domain': [('type', '=', 'bank')]}
            return res
        # TODO journal & acc pay meth setup

        with patch.object(AccountPaymentMethod, '_get_payment_method_information', _get_payment_method_information):
            cls.env['account.payment.method'].create({
                'name': 'Dummy method',
                'code': 'none',
                'payment_type': 'inbound'
            })

        cls.dummy_acquirer.journal_id = cls.company_data['default_journal_bank'].id,

        cls.account = cls.company.account_journal_payment_credit_account_id
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'line_ids': [
                (0, 0, {
                    'account_id': cls.account.id,
                    'currency_id': cls.currency_euro.id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                }),
                (0, 0, {
                    'account_id': cls.account.id,
                    'currency_id': cls.currency_euro.id,
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -200.0,
                }),
            ],
        })

    def setUp(self):
        super().setUp()
        # Disable _reconcile_after_done patcher
        self.reconcile_after_done_patcher.stop()
