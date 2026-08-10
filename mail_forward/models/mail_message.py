# Copyright 2024 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, models
from odoo.tools import format_datetime



class MailMessage(models.Model):
      _inherit = "mail.message"

      def action_wizard_forward(self):
        view = self.env.ref("mail.email_compose_message_wizard_form")
        action = self.env["ir.actions.actions"]._for_xml_id("mail.action_email_compose_message_wizard")

        partner_ids=[]
        if self.model in ['crm.lead','sale.order']:
             lead=self.env[self.model].browse(self.res_id)
             if lead.partner_id:
                  partner_ids.append(lead.partner_id.id)
    
        action["name"] = _("Forward Message")
        action["view_mode"] = view.type
        action["views"] = [(view.id, view.type)]
        action["context"] = {
            "default_model": self.model if self.model else "mail.thread",  # ✅ Ensure model is valid
            "default_res_ids": [self.res_id] if self.res_id else [],  # ✅ Fix: Convert to a list
            "default_composition_mode": "comment",
            "default_body": self._build_message_body_for_forward(),
            "default_attachment_ids": self.attachment_ids.ids,
            "default_is_log": False,
            "default_notify": True,
            "force_email": True,
            "message_forwarded_id": self.id,
            "default_partner_ids": partner_ids,
        }
    
        return action


      def _build_message_body_for_forward(self):
          partner_emails = [
              partner.email_formatted
              for partner in self.partner_ids
              if partner.email_formatted
          ]
      
          salesperson_signature = ""
          employee_name = ""
          employee_phone = ""
          employee_email = ""
      
          # ✅ Fetch related record (CRM Lead or Sale Order)
          if self.model in ["crm.lead", "sale.order"] and self.res_id:
              related_record = self.env[self.model].browse(self.res_id)
              if related_record and related_record.user_id:
                  employee_name = related_record.user_id.name
                  employee_email = related_record.user_id.email
                  employee_phone = related_record.user_id.mobile or ""  # Fetch phone
                  salesperson_signature = related_record.user_id.signature or ""
      
          return """
              <br/><br/>
              {signature}
              <hr/>
              <br/><strong>{employee_name}</strong><br/>
              <p>{employee_phone} |  {employee_email}</p>
              <br/>
              {str_forwarded_message}<br/>
              {str_from}: {email_from}<br/>
              {str_date}: {date}<br/>
              {str_subject}: {subject}<br/>
              {str_to}: {to}<br/>
              <br/><br/>
              {body}
          """.format(
              str_forwarded_message=_("---------- Forwarded message ---------"),
              email_from=self.email_from,
              date=format_datetime(self.env, self.create_date),
              subject=self.subject,
              to=", ".join(partner_emails),
              str_date=_("Date"),
              str_subject=_("Subject"),
              str_from=_("From"),
              str_to=_("To"),
              body=self.body,
              signature=salesperson_signature,  # ✅ Adding Signature
              employee_name=employee_name,
              employee_email=employee_email,
              employee_phone=employee_phone
          )

    
          
    
      # def _build_message_body_for_forward(self):
      #       partner_emails = [
      #           partner.email_formatted
      #           for partner in self.partner_ids
      #           if partner.email_formatted
      #       ]

      #       salesperson_signature = ""
      #       employee_name=""
      #       employee_phone=""
      #       employee_email=""

      #       # ✅ Fetch related record (CRM Lead or Sale Order)
      #       if self.model in ["crm.lead", "sale.order"] and self.res_id:
      #               related_record = self.env[self.model].browse(self.res_id)
      #               if related_record and related_record.user_id:
      #                   employee_name = related_record.user_id.name
      #                   employee_email = related_record.user_id.email
      #                   salesperson_signature = related_record.user_id.signature or ""
      #       return """
      #           <br/><br/>
      #           {signature}
      #           <create one line this place >
      #           <strong>{employee_name}</strong>
      #           <p>{employee_phone}</p> | <p>{employee_email}</p>
      #           {str_forwarded_message}<br/>
      #           {str_from}: {email_from}<br/>
      #           {str_date}: {date}<br/>
      #           {str_subject}: {subject}<br/>
      #           {str_to}: {to}<br/>
      #           <br/><br/>
      #           {body}
               
               
      #       """.format(
      #           str_forwarded_message=_("---------- Forwarded message ---------"),
      #           email_from=self.email_from,
      #           date=format_datetime(self.env, self.create_date),
      #           subject=self.subject,
      #           to=", ".join(partner_emails),
      #           str_date=_("Date"),
      #           str_subject=_("Subject"),
      #           str_from=_("From"),
      #           str_to=_("To"),
      #           body=self.body,
      #           signature=salesperson_signature  # ✅ Adding Signature
      #       )
    
    
    
    
    
    
