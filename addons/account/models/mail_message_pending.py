from odoo import fields, models
import base64


class MessageTemp(models.Model):
    """ Class representing a temporary message store in the database.
        Such message could represent message waitint for some kind of validation
        for example an EDI. Contains data of the mail message that will be
        posted when the validation authorises it.
    """
    _name = "mail.message.pending"
    _description = "Message to be post later"
    _order = "id desc"

    email_add_signature = fields.Boolean(default=True)
    mail_auto_delete = fields.Boolean(default=True)
    subject = fields.Char('Subject')
    body = fields.Html('Contents', default='', sanitize_style=True)
    parent_id = fields.Many2one(
        'mail.message', 'Parent Message', index='btree_not_null', ondelete='set null',
        help="Initial thread message.")
    partner_ids = fields.Many2many('res.partner', string='Recipients', context={'active_test': False})
    attachment_ids = fields.Many2many(
        'ir.attachment', 'message_pending_attachment_rel',
        'message_pending_id', 'attachment_id',
        string='Attachments',
        help='Attachments are linked to a document through model / res_id and to the message '
             'through this field.')
    author_id = fields.Many2one(
        'res.partner', 'Author', index=True, ondelete='set null',
        help="Author of the message. If not set, email_from may hold an email address that did not match any partner.")
    email_from = fields.Char('From', help="Email address of the sender. This field is set when no matching partner is found and replaces the author_id field in the chatter.")
    account_edi_document_ids = fields.Many2many('account.edi.document', 'mail_message_pending_account_edi_document_rel',
        'mail_message_pending_id', 'account_edi_document_id', string="Account EDI Document")
    template_id = fields.Many2one("mail.template", "Mail Template")
    account_move_id = fields.Many2one("account.move", "Account Move ID")
    is_posted = fields.Boolean(default=False)


    def get_post_values(self, mail_message_id):
        mail_message_pending = self.env['mail.message.pending'].browse(mail_message_id)
        post_params = {
            'message_type': 'comment',
            'subtype_id': 1,
            'email_layout_xmlid': 'mail.mail_notification_paynow',
            'email_add_signature': mail_message_pending.email_add_signature,
            'mail_auto_delete': mail_message_pending.mail_auto_delete,
            'model_description': 'Invoice',
            'subject': mail_message_pending.subject,
            'body': mail_message_pending.body,
            'parent_id': mail_message_pending.parent_id.id,
            'partner_ids': mail_message_pending.mapped('partner_ids').ids,
            'attachment_ids': mail_message_pending.mapped('attachment_ids').ids,
            'author_id': mail_message_pending.author_id.id,
            'email_from': mail_message_pending.email_from,
            'record_name': False,
            'reply_to_force_new': False,
            'mail_server_id': False,
            'mail_activity_type_id': False,
            'state': 'cancel',
            'failure_type': 'mail_email_missing'
        }
        return post_params

    def update_report(self, res_id):
        """"
            Update the invoice report associate with the message and put it in the
            attachment of the invoice.
        """
        mail_message_pending = self.env['mail.message.pending'].browse(res_id)
        report_template = mail_message_pending.template_id.report_template
        pdf_content, _ = report_template._render_qweb_pdf([mail_message_pending.account_move_id.id])
        report = self.env['ir.attachment'].browse(self._get_invoice_report_id(res_id))
        report.write({
            'datas' : base64.b64encode(pdf_content),
            'res_id' : mail_message_pending.account_move_id.id,
            'res_model' : 'account.move'
        })
        mail_message_pending.write({
            'is_posted' : True
        })

    def _get_invoice_report_id(self, res_id):
        mail_message_pending = self.env['mail.message.pending'].browse(res_id)
        ir_attachment_id = mail_message_pending.mapped('attachment_ids').id
        return ir_attachment_id
