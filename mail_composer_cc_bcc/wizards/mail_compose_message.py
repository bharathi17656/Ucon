
import ast
import datetime
import json
import logging
import psycopg2
import pytz
import re
import smtplib
import threading
from collections import defaultdict

from dateutil.parser import parse

from odoo import _, api, fields, models, modules, SUPERUSER_ID, tools
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.modules.registry import Registry

from bs4 import BeautifulSoup

import ssl

_logger = logging.getLogger(__name__)



class MailDeliveryException(Exception):
    """Specific exception subclass for mail delivery errors"""


def make_wrap_property(name):
    return property(
        lambda self: getattr(self.__obj__, name),
        lambda self, value: setattr(self.__obj__, name, value),
    )


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    partner_cc_ids = fields.Char(
        "Cc",
        help="Enter email addresses for CC, separated by commas."
    )
    partner_bcc_ids = fields.Char(
        "Bcc",
        help="Enter email addresses for BCC, separated by commas."
    )

    def _action_send_mail(self, auto_commit=False):

        print("this is my send mail 1")
        """Override the original method to add CC/BCC and remove unwanted divs."""
        if self.composition_mode == "mass_mail":
            return super()._action_send_mail(auto_commit)

        # Get the "To" recipients
        to_list = [partner.email for partner in self.partner_ids if partner.email]
        if not to_list:
            raise ValueError("❌ No recipient found for the email (To field).")

        # Get the "CC" recipients
        cc_list = []
        if isinstance(self.partner_cc_ids, str):  # If it's a string (comma-separated emails)
            cc_list = tools.email_split(self.partner_cc_ids)
        elif self.partner_cc_ids:  # If it's a recordset
            cc_list = [partner.email for partner in self.partner_cc_ids if partner.email]


        # gm_email = "gm@uconqatar.com"
        # if gm_email not in cc_list:
        #     cc_list.append(gm_email)

        # Ensure emails are properly formatted
        email_to_str = ",".join(tools.email_split(",".join(to_list)))
        email_cc_str = ",".join(tools.email_split(",".join(cc_list))) if cc_list else ""

        # Call the original method to create the email
        res = super()._action_send_mail(auto_commit=auto_commit)
        print("this is my send mail 1-2",res)
        # Fetch the latest mail
        mail = self.env['mail.mail'].sudo().search([], order="id desc", limit=1)
        print("this is my send mail 2")
        if mail:
            # Update the email headers before sending
            mail.write({
                'email_to': email_to_str,  # Ensure proper To field
                'email_cc': email_cc_str   # Ensure CC is properly added
            })

            print("this is my send mail 3")

            # Use BeautifulSoup to remove unwanted divs
            if mail.body_html:
                soup = BeautifulSoup(mail.body_html, "html.parser")

                # Remove the div with summary="o_mail_notification"
                for div in soup.find_all("div", {"summary": "o_mail_notification"}):
                    div.decompose()

                # Remove the hidden preview div
                for div in soup.find_all("div", {"style": "display: none; max-height: 0px; overflow: hidden; color:#fff; font-size:0px; line-height:0px"}):
                    div.decompose()

                # Update the email body without unwanted content
                mail.body_html = str(soup)

            # Send the email only once with the correct headers
            if self.force_send:
                print("this is my send forse send",self.force_send)
                result=mail.send(auto_commit=auto_commit)
                
                print("this is my send mail 4",result)

            

        return res



class IrMailServer(models.Model):
    """Represents an SMTP server, able to send outgoing emails, with SSL and TLS capabilities."""
    _inherit = "ir.mail_server"

    def _prepare_email_message(self, message, smtp_session):
        """Override to ensure CC headers are correctly formatted."""
        # Call the original method to get the email details
        smtp_from, smtp_to_list, message = super()._prepare_email_message(message, smtp_session)
        print("this is my prepare mail 1")
        # Ensure only one CC header exists
        if 'Cc' in message:
            print("this is my prepare mail 2")
            email_cc = message['Cc']
            message.replace_header('Cc', email_cc)  # Replace existing Cc header
        elif hasattr(message, 'email_cc') and message.email_cc:
            print("this is my prepare mail 3")
            message.add_header('Cc', message.email_cc)  # Add Cc header if missing
        print("this is prepare header ", smtp_from, smtp_to_list, message)
        return smtp_from, smtp_to_list, message

    def send_email(self, message, mail_server_id=None, smtp_server=None, smtp_port=None,
                   smtp_user=None, smtp_password=None, smtp_encryption=None,
                   smtp_ssl_certificate=None, smtp_ssl_private_key=None,
                   smtp_debug=False, smtp_session=None, *args, **kwargs):
        """Override send_email to ensure CC headers are correctly formatted."""
        print("this is my send email 1")
        smtp = smtp_session
        if not smtp:
            smtp = self.connect(
                smtp_server, smtp_port, smtp_user, smtp_password, smtp_encryption,
                smtp_from=message['From'], ssl_certificate=smtp_ssl_certificate, ssl_private_key=smtp_ssl_private_key,
                smtp_debug=smtp_debug, mail_server_id=mail_server_id,
            )

        smtp_from, smtp_to_list, message = self._prepare_email_message(message, smtp)
        print("this is send email part ", smtp_from,smtp_to_list)
        # if smtp_to_list is None or not smtp_to_list:
        #     print("this is my send email 2")
        #     _logger.info("Skipping email as there are no valid recipients.")
        #     return True  # Return success instead of an error

        # return super().send_email(message, *args, **kwargs)

        # Do not actually send emails in testing mode!
        try:
            message_id = message['Message-Id']

            smtp.send_message(message, smtp_from, smtp_to_list)

            # do not quit() a pre-established smtp_session
            if not smtp_session:
                smtp.quit()
        except smtplib.SMTPServerDisconnected:
            raise
        except Exception as e:
            msg = _(
                "Mail delivery failed via SMTP server '%(server)s'.\n%(exception_name)s: %(message)s",
                server=smtp_server,
                exception_name=e.__class__.__name__,
                message=e,
            )
            _logger.info(msg)
            raise MailDeliveryException(_("Mail Delivery Failed"), msg)
        print("this is out send rmail result",message_id)
        
        return message_id
    





class MailMail(models.Model):
    _inherit = 'mail.mail'
    _description = 'Outgoing Mails'
    _inherits = {'mail.message': 'mail_message_id'}


  
        

    def _prepare_outgoing_list(self, mail_server=False, recipients_follower_status=None):
        """
        Return a list of emails to send based on current mail.mail.
        :param mail_server: <ir.mail_server> mail server that will be used to send the mails,
          False if it is the default one
        :param recipients_follower_status: see ``Followers._get_mail_recipients_follower_status()``
        :return list: list of dicts used in IrMailServer.build_email()
        """
        self.ensure_one()
        body = self._prepare_outgoing_body()

        # Prepare headers
        headers = {}
        if self.headers:
            try:
                headers = ast.literal_eval(self.headers)
            except (ValueError, TypeError) as e:
                _logger.warning('Evaluation error in mail headers: %s', e)
            except Exception as e:
                _logger.warning('Unknown error in mail headers: %s', e)
        
        headers['X-Odoo-Message-Id'] = self.message_id
        headers.setdefault('Return-Path', self.record_alias_domain_id.bounce_email or self.env.company.bounce_email)

        # Prepare recipients
        email_list = []
        if self.email_to:
            email_to_normalized = tools.mail.email_normalize_all(self.email_to)
            email_to = tools.mail.email_split_and_format_normalize(self.email_to)
            email_list.append({
                'email_cc': [],
                'email_to': email_to,
                'email_to_normalized': email_to_normalized,
                'email_to_raw': self.email_to or '',
                'partner_id': False,
            })
        
        if self.email_cc:
            email_cc_normalized = tools.mail.email_normalize_all(self.email_cc)
            if email_list:
                email_list[0]['email_cc'] = tools.mail.email_split_and_format_normalize(self.email_cc)
                email_list[0]['email_to_normalized'] += email_cc_normalized
            else:
                email_list.append({
                    'email_cc': tools.mail.email_split_and_format_normalize(self.email_cc),
                    'email_to': [],
                    'email_to_normalized': email_cc_normalized,
                    'email_to_raw': False,
                    'partner_id': False,
                })

        # Process recipient partners
        for partner in self.recipient_ids:
            email_to_normalized = tools.mail.email_normalize_all(partner.email)
            existing_emails = {email for entry in email_list for email in entry['email_to_normalized']}
            if set(email_to_normalized).intersection(existing_emails):
                continue  # Skip duplicates

            email_to = [tools.formataddr((partner.name or "", email or "False")) for email in email_to_normalized or [partner.email]]
            email_list.append({
                'email_cc': [],
                'email_to': email_to,
                'email_to_normalized': email_to_normalized,
                'email_to_raw': partner.email or '',
                'partner_id': partner,
            })

        # Process attachments
        attachments = self.attachment_ids
        if body and attachments:
            link_ids = {int(link) for link in re.findall(r'/web/(?:content|image)/([0-9]+)', body)}
            if link_ids:
                attachments = attachments - self.env['ir.attachment'].browse(list(link_ids))
        
        record_owned_attachments = attachments.sudo().filtered(lambda a: a.res_model and a.res_id and a.res_model != 'mail.message')
        estimated_email_size_bytes = self._estimate_email_size(headers, body, [a.file_size for a in attachments.sudo()])
        max_email_size_bytes = (mail_server or self.env['ir.mail_server']).sudo()._get_max_email_size() * 1024 * 1024

        if estimated_email_size_bytes > max_email_size_bytes:
            record_owned_attachments.sudo().generate_access_token()
            attachments_links = self.env['ir.qweb']._render('mail.mail_attachment_links', {'attachments': record_owned_attachments})
            body = tools.mail.append_content_to_html(body, attachments_links, plaintext=False)
            attachments -= record_owned_attachments
        
        email_attachments = [(a['name'], a['raw'], a['mimetype']) for a in attachments.sudo().read(['name', 'raw', 'mimetype']) if a['raw'] is not False]
        
        # Build final email list
        results = []
        _logger.info("Prepared outgoing email list: %s", email_list)
        for email_values in email_list:
            partner_id = email_values['partner_id']
            body_personalized = self._personalize_outgoing_body(body, partner_id, recipients_follower_status)
            results.append({
                'attachments': email_attachments,
                'body': body_personalized,
                'body_alternative': tools.html2plaintext(body_personalized),
                'email_cc': email_values['email_cc'],
                'email_from': self.email_from,
                'email_to': email_values['email_to'],
                'email_to_normalized': email_values['email_to_normalized'],
                'email_to_raw': email_values['email_to_raw'],
                'headers': headers,
                'message_id': self.message_id,
                'object_id': f'{self.res_id}-{self.model}' if self.res_id else '',
                'partner_id': partner_id,
                'references': self.references,
                'reply_to': [self.email_from,self.reply_to],
                'subject': self.subject,
            })
        
        return results





    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None, alias_domain_id=False,
              mail_server=False, post_send_callback=None):
        IrMailServer = self.env['ir.mail_server']
        # Only retrieve recipient followers of the mails if needed
        mails_with_unfollow_link = self.filtered(lambda m: m.body_html and '/mail/unfollow' in m.body_html)
        recipients_follower_status = (
            None if not mails_with_unfollow_link
            else (
                self.env['mail.followers']._get_mail_recipients_follower_status(mails_with_unfollow_link.ids)
                if hasattr(self.env['mail.followers'], '_get_mail_recipients_follower_status')
                else {}
            )
        )

        mail_len=len(self.ids)
        current_mail=1

        for mail_id in self.ids:
            success_pids = []
            failure_reason = None
            failure_type = None
            mail = None
            try:
                mail = self.browse(mail_id)
                if mail.state != 'outgoing':
                    continue

                # Writing on the mail object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure earlier
                mail.write({
                    'state': 'exception',
                    'failure_reason': _('Error without exception. Probably due to sending an email without computed recipients.'),
                })
                # Update notification in a transient exception state to avoid concurrent
                # update in case an email bounces while sending all emails related to current
                # mail record.
                notifs = self.env['mail.notification'].search([
                    ('notification_type', '=', 'email'),
                    ('mail_mail_id', 'in', mail.ids),
                    ('notification_status', 'not in', ('sent', 'canceled'))
                ])
                if notifs:
                    notif_msg = _('Error without exception. Probably due to concurrent access update of notification records. Please see with an administrator.')
                    notifs.sudo().write({
                        'notification_status': 'exception',
                        'failure_type': 'unknown',
                        'failure_reason': notif_msg,
                    })
                    # `test_mail_bounce_during_send`, force immediate update to obtain the lock.
                    # see rev. 56596e5240ef920df14d99087451ce6f06ac6d36
                    notifs.flush_recordset(['notification_status', 'failure_type', 'failure_reason'])

                # protect against ill-formatted email_from when formataddr was used on an already formatted email
                emails_from = tools.mail.email_split_and_format_normalize(mail.email_from)
                email_from = emails_from[0] if emails_from else mail.email_from

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None
                # TDE note: could be great to pre-detect missing to/cc and skip sending it
                # to go directly to failed state update
                email_list = mail._prepare_outgoing_list(
                    mail_server=mail_server or mail.mail_server_id,
                    recipients_follower_status=recipients_follower_status,
                )

                _logger.info("this is my email user from is ",email_from)

                print("email list is ", email_list)

                # send each sub-email
                for email in email_list:

                    print("this is loop of email",email)
                    # give indication to 'send_mail' about emails already considered
                    # as being valid
                    email_to_normalized = email.pop('email_to_normalized', [])

                    if  mail.model == 'crm.lead' and mail.res_id:
                        print("this is crm record id of mail", mail.res_id)

                        lead = self.env['crm.lead'].browse(mail.res_id)
                        salesperson_email = lead.user_id.partner_id.email if lead.user_id and lead.user_id.partner_id else None

                        print("this is our salesperson mail id", salesperson_email)

                        if salesperson_email:
                            for email_entry in email_list:  # Iterate over list items properly
                                # if salesperson_email not in email_entry['email_to'] and salesperson_email not in email_entry['email_cc']:
                                #     email_entry['email_cc'].append(salesperson_email)  # Append email to list
                                if salesperson_email not in email_to_normalized:
                                    if mail_len == current_mail:
                                        email_to_normalized.append(salesperson_email)
                                       
                                    email_entry['email_cc'].append(salesperson_email)  # Append email to list
                                    current_mail+=1

                    if mail.model == 'sale.order' and mail.res_id:
                        print("this is sale record id of mail", mail.res_id)

                        lead = self.env['sale.order'].browse(mail.res_id)
                        salesperson_email = lead.user_id.partner_id.email if lead.user_id and lead.user_id.partner_id else None

                        print("this is our salesperson mail id", salesperson_email)

                        if salesperson_email:
                            for email_entry in email_list:  # Iterate over list items properly
                                # if salesperson_email not in email_entry['email_to'] and salesperson_email not in email_entry['email_cc']:
                                #  email_entry['email_cc'].append(salesperson_email)  # Append email to list

                                if salesperson_email not in email_to_normalized:
                                    if mail_len == current_mail:
                                        email_to_normalized.append(salesperson_email)
                                       
                                    email_entry['email_cc'].append(salesperson_email)  # Append email to list
                                    current_mail+=1

                    print("this is llop in email normalize",email_to_normalized)
                    email['body'] = re.sub(
                                        r'(<div summary="o_mail_notification")',
                                        r'\1 style="display: none !important;"',
                                        email['body']
                                    )
                    # if given, contextualize sending using alias domains
                    # if alias_domain_id:
                    #     alias_domain = self.env['mail.alias.domain'].sudo().browse(alias_domain_id)
                    #     SendIrMailServer = IrMailServer.with_context(
                    #         domain_notifications_email=alias_domain.default_from_email,
                    #         domain_bounce_address=email['headers'].get('Return-Path') or alias_domain.bounce_email,
                    #         send_validated_to=email_to_normalized,
                    #     )
                    # else:
                    SendIrMailServer = IrMailServer.with_context(send_validated_to=email_to_normalized)
                    build_email_fn = (
                        getattr(SendIrMailServer, '_build_email', None)
                        or getattr(SendIrMailServer, 'build_email', None)
                        or getattr(IrMailServer, '_build_email', None)
                        or getattr(IrMailServer, 'build_email', None)
                    )
                    msg = build_email_fn(
                        email_from=email_from,
                        email_to=email['email_to'],
                        subject=email['subject'],
                        body=email['body'],
                        body_alternative=email['body_alternative'],
                        email_cc=email['email_cc'],
                        reply_to=email['reply_to'],
                        attachments=email['attachments'],
                        message_id=email['message_id'],
                        references=email['references'],
                        object_id=email['object_id'],
                        subtype='html',
                        subtype_alternative='plain',
                        headers=email['headers'],
                    )
                    processing_pid = email.pop("partner_id", None)
                    print("this is message to set build",msg)
                    try:
                        res = SendIrMailServer.send_email(
                            msg, mail_server_id=mail.mail_server_id.id, smtp_session=smtp_session)
                        if processing_pid:
                            success_pids.append(processing_pid)
                        processing_pid = None
                    except AssertionError as error:
                        if str(error) == IrMailServer.NO_VALID_RECIPIENT:
                            # if we have a list of void emails for email_list -> email missing, otherwise generic email failure
                            if not email.get('email_to') and failure_type != "mail_email_invalid":
                                failure_type = "mail_email_missing"
                            else:
                                failure_type = "mail_email_invalid"
                            # No valid recipient found for this particular
                            # mail item -> ignore error to avoid blocking
                            # delivery to next recipients, if any. If this is
                            # the only recipient, the mail will show as failed.
                            _logger.info("Ignoring invalid recipients for mail.mail %s: %s",
                                         mail.message_id, email.get('email_to'))
                        else:
                            raise
                if res:  # mail has been sent at least once, no major exception occurred
                    mail.write({'state': 'sent', 'message_id': res, 'failure_reason': False})
                    if not modules.module.current_test:
                        _logger.info(
                            "Mail with ID %r and Message-Id %r from %r to (redacted) %r successfully sent",
                            mail.id,
                            mail.message_id,
                            tools.email_normalize(msg['from']),
                            tools.mail.email_anonymize(tools.email_normalize(msg['to']))
                        )
                    # /!\ can't use mail.state here, as mail.refresh() will cause an error
                    # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr in 6.1
                try:
                    mail._postprocess_sent_message(success_pids=success_pids, failure_type=failure_type, success_emails=None)
                except TypeError:
                    mail._postprocess_sent_message(success_pids=success_pids, failure_type=failure_type)
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception(
                    'MemoryError while processing mail with ID %r and Msg-Id %r. Consider raising the --limit-memory-hard startup option',
                    mail.id, mail.message_id)
                # mail status will stay on ongoing since transaction will be rollback
                raise
            except (psycopg2.Error, smtplib.SMTPServerDisconnected):
                # If an error with the database or SMTP session occurs, chances are that the cursor
                # or SMTP session are unusable, causing further errors when trying to save the state.
                _logger.exception(
                    'Exception while processing mail with ID %r and Msg-Id %r.',
                    mail.id, mail.message_id)
                raise
            except Exception as e:
                if isinstance(e, AssertionError):
                    # Handle assert raised in IrMailServer to try to catch notably from-specific errors.
                    # Note that assert may raise several args, a generic error string then a specific
                    # message for logging in failure type
                    error_code = e.args[0]
                    if len(e.args) > 1 and error_code == IrMailServer.NO_VALID_FROM:
                        # log failing email in additional arguments message
                        failure_reason = str(e.args[1])
                    else:
                        failure_reason = error_code
                    if error_code == IrMailServer.NO_VALID_FROM:
                        failure_type = "mail_from_invalid"
                    elif error_code in (IrMailServer.NO_FOUND_FROM, IrMailServer.NO_FOUND_SMTP_FROM):
                        failure_type = "mail_from_missing"
                # generic (unknown) error as fallback
                if not failure_reason:
                    failure_reason = tools.exception_to_unicode(e)
                if not failure_type:
                    failure_type = "unknown"

                _logger.exception('failed sending mail (id: %s) due to %s', mail.id, failure_reason)
                mail.write({
                    "failure_reason": failure_reason,
                    "failure_type": failure_type,
                    "state": "exception",
                })
                try:
                    mail._postprocess_sent_message(
                        success_pids=success_pids,
                        failure_reason=failure_reason, failure_type=failure_type,
                        success_emails=None
                    )
                except TypeError:
                    mail._postprocess_sent_message(
                        success_pids=success_pids,
                        failure_reason=failure_reason, failure_type=failure_type
                    )
                if raise_exception:
                    if isinstance(e, (AssertionError, UnicodeEncodeError)):
                        if isinstance(e, UnicodeEncodeError):
                            value = "Invalid text: %s" % e.object
                        else:
                            value = '. '.join(e.args)
                        raise MailDeliveryException(value)
                    raise
            if auto_commit is True:
                if post_send_callback:
                    post_send_callback([mail_id])
                self._cr.commit()
        if post_send_callback:
            post_send_callback(self.ids)

        return True

