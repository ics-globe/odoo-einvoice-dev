# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing_sms.tests.common import MassSMSCommon
from odoo.tests.common import users

class TestRetryCronTrigger(MassSMSCommon):

    @users('user_marketing')
    def test_mailing_retry_immediate_trigger(self):
        default_list_ids = self.env['mailing.list'].with_context(self._test_context).create({
            'name': 'ListC',
            'contact_ids': [
                (0, 0, {'name': 'test', 'email': 'test@odoo.com', 'mobile': '+91 1234567890'}),
            ]
        }).ids
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestMailing',
            'subject': 'Test',
            'mailing_type': 'sms',
            'body_plaintext': 'Coucou hibou',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'contact_list_ids': default_list_ids,
        })
        mailing.action_send_sms()

        # Send the SMS, which leads to RETRY because IAP server is not available
        self.env.ref('sms.ir_cron_sms_scheduler_action').sudo().method_direct_trigger()

        process_queue_cron = self.env.ref('mass_mailing.ir_cron_mass_mailing_queue')
        IrCronTrigger = self.env['ir.cron.trigger'].sudo()
        prev_count = IrCronTrigger.search_count([('cron_id', '=', process_queue_cron.id)])

        # Retry
        mailing.action_retry_failed()
        current_count = IrCronTrigger.search_count([('cron_id', '=', process_queue_cron.id)])

        self.assertEqual(current_count, prev_count + 1, "Should have created an additional trigger immediately")
