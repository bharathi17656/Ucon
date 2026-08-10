# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging
import re
import smtplib

import psycopg2
from odoo import _, fields, models, tools,api
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.tools import email_split

_logger = logging.getLogger(__name__)


def format_emails(partners):
    """Format partner emails for use in email headers."""
    return ", ".join(
        tools.formataddr((p.name or "False", p.email and tools.mail._normalize_email(p.email) or "False"))
        for p in partners
    )



class MailMail(models.Model):
    _inherit = "mail.mail"

    email_bcc = fields.Char("Bcc", help="Blind Cc message recipients")

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None, **kwargs):
        # Ensure the BCC field is properly set
        # if self.email_bcc:
        #     print('This is the email bcc', self.email_bcc)
        #     bcc_emails = email_split(self.email_bcc)
        #     self.sudo().write({'email_bcc': ",".join(bcc_emails)})

        # Call the super method to send the mail
        res = super()._send(auto_commit=auto_commit, raise_exception=raise_exception, smtp_session=smtp_session, **kwargs)
        print('This is the send method result', res)
        return res



    # def build_email(self, email, attachments=None, headers=None):
    #     print('this is the build email method',email,attachments,headers)
    #     env = self.env
    #     mail = self
    #     email_from = email.get("email_from")
    #     IrMailServer = env["ir.mail_server"]

    #     # Ensure BCC is properly formatted as a list
    #     email_bcc_list = email.get("email_bcc", "").split(",") if email.get("email_bcc") else []

    #     # Print BCC emails for debugging
    #     print("Building email with BCC:", email_bcc_list)

    #     msg = IrMailServer.build_email(
    #         email_from=email_from,
    #         email_to=email.get("email_to"),
    #         subject=mail.subject,
    #         body=email.get("body"),
    #         body_alternative=email.get("body_alternative"),
    #         email_cc=email.get("email_cc"),
    #         email_bcc=email_bcc_list,  # Ensure email_bcc is added correctly
    #         reply_to=mail.reply_to,
    #         attachments=attachments,
    #         message_id=mail.message_id,
    #         references=mail.references,
    #         object_id=mail.res_id and ("%s-%s" % (mail.res_id, mail.model)),
    #         subtype="html",
    #         subtype_alternative="plain",
    #         headers=headers,
    #     )
    #     return msg




    # def _send_prepare_values(self, partner=None):

    #     print('this is the send prepare values method')
    #     res = super()._send_prepare_values(partner=partner)
    #     is_from_composer = self.env.context.get("is_from_composer", False)

    #     if not is_from_composer:
    #         return res

    #     partners_cc_bcc = self.recipient_cc_ids + self.recipient_bcc_ids
    #     partner_to_ids = [r.id for r in self.recipient_ids if r not in partners_cc_bcc]
    #     partner_to = self.env["res.partner"].browse(partner_to_ids)

    #     res["email_to"] = format_emails(partner_to)
    #     res["email_cc"] = format_emails(self.recipient_cc_ids)
    #     res["email_bcc"] = format_emails(self.recipient_bcc_ids)

    #     # Print BCC recipients for debugging
    #     print("BCC Recipients Before Sending:", res["email_bcc"])

    #     return res








from odoo.tools.mail import (
    append_content_to_html, decode_message_header, email_normalize, email_split,
    email_split_and_format, formataddr, html_sanitize,
    generate_tracking_message_id,
    unfold_references,
)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        routes = super().message_route(message, message_dict, model, thread_id, custom_values)

        # Extract required details
        email_to_list = [e.lower() for e in email_split(message_dict['to'])]
        in_reply_to = message_dict.get('in_reply_to', '')
        email_subject= message_dict.get('subject', '')
        email_body=message_dict.get('body', '')

        message_id = message_dict['message_id']

       
        thread_references = message_dict['references'] or message_dict['in_reply_to']
        msg_references = [r.strip() for r in unfold_references(thread_references) if 'reply_to' not in r]
     
        msg_references = msg_references[-32:]
        
        replying_to_msg = self.env['mail.message'].sudo().search(
            [('message_id', 'in', msg_references)], limit=1, order='id desc'
        ) if msg_references else self.env['mail.message']
        is_a_reply, reply_model, reply_thread_id = bool(replying_to_msg), replying_to_msg.model, replying_to_msg.res_id

        # author and recipients
        email_from = message_dict['email_from']
        


        # Print details
        print("\n---- Extracted Email Details ----")
        print("Reply-To:", in_reply_to)
        print("Email To List:", email_to_list)
        print("Model:", reply_model)
        print("Res ID:", reply_thread_id)
        print("Reply ID:", is_a_reply)
        print("----------------------------------\n")


        if reply_model and reply_thread_id and is_a_reply:
            lead=self.env[reply_model].browse(reply_thread_id)
            salesperson_email = lead.user_id.partner_id.email if lead.user_id and lead.user_id.partner_id else None

            print("this is our salesperson mail id", salesperson_email)

            if salesperson_email and salesperson_email.lower() not in email_to_list:
                print("Sending email to salesperson:", salesperson_email)

                print("this is our mail route of message_dict",message_dict)

                # Prepare the email data
                mail_values = {
                    'subject': f"Fwd: {email_subject}",
                    'body_html': f"<p>{email_body}</p>",  # Forward the original message
                    'email_from': email_from,  # Keep the sender same as the original email
                    'email_to': salesperson_email,  # Send to the salesperson
                }

                # Create and send the email
                mail = self.env['mail.mail'].sudo().create(mail_values)
                mail.sudo().send()

                print("Email sent to salesperson successfully!")


        return routes


