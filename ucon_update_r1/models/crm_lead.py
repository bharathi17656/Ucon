from odoo import models, fields, api,exceptions
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)



 
class QuotationStageMapping(models.Model):
    _name = 'quotation.stage.mapping'
    _description = 'Quotation State to CRM Lead Stage Mapping'

    sale_order_state = fields.Selection([
        ('draft', 'Quotation Completed'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sale Order'),
        ('done', 'Done'),
        ('partial','Partial Amount')
    ], string='Sale Order State', required=True)

    crm_lead_stage = fields.Many2one('crm.stage', string='CRM Lead Stage', required=True)






class Lead(models.Model):
    _inherit = 'crm.lead'

    rfq_number=fields.Char(string='RFQ Reference Number')



    def check_submitted_overdue_leads(self):
        quote_completed_stage = self.env['crm.stage'].search([('name', 'in', ['Quote Preparation','Discovery'])])
       
        for lead in quote_completed_stage:
            if lead :
                deadline = fields.Datetime.now() - timedelta(hours=2)

                overdue_leads = self.env['crm.lead'].search([
                    ('stage_id', '=', lead.id),
                    ('date_last_stage_update', '<=', deadline)
                ])

                template = self.env.ref('ucon_update_r1.alert_email_completed_lead_overdue_template_sales_person')
                for lead in overdue_leads:
                    if template:
                        template.send_mail(lead.id, force_send=True)



    @api.model
    def create_scheduled_action(self):
        self.env['ir.cron'].create({
            'name': 'Check Completed Leads Overdue ',
            'user_id': self.env.user.id,
            'model_id': self.env.ref('crm.model_crm_lead').id,  # The model this cron job will run for
            'state': 'code',
            'code': 'model.check_submitted_overdue_leads()',  # The method to call
            'interval_type': 'days',
            'interval_number': 1,  # Run it every day
            'active': True,
        })



    def check_no_activity_leads(self):
        leads = self.env['crm.lead'].search([])

        for lead in leads:

            if lead :
              if lead.stage_id.name != 'Won':
                print("lead number",lead)
                deadline = fields.Datetime.now() - timedelta(hours=48)

                overdue_activity = self.env['mail.activity'].search([
                                    ('res_model', '=', 'crm.lead'),
                                    ('res_id', '=', lead.id),
                                    ('active','in',[True,False])  
                                ], order="date_deadline desc", limit=1)  # Fetch the most recent activity
                
                print("this is activity list",overdue_activity,lead.id)

                if overdue_activity  :
                   
                    for activity in overdue_activity:
                      
                        if activity.active :
                            print("this is have activity",activity.id,lead.id)
                        else:
                            if activity.date_deadline:
                                if activity.date_deadline <= deadline:
                                    template = self.env.ref('ucon_update_r1.alert_email_no_activity_lead_template_sales_person')
                                    if template:
                                        template.send_mail(lead.id, force_send=True)
                else:
                    
                    if lead.date_last_stage_update:
                        if lead.date_last_stage_update <= deadline:
                    
                             template = self.env.ref('ucon_update_r1.alert_email_no_activity_lead_template_sales_person')
                             if template:
                                        template.send_mail(lead.id, force_send=True)





    @api.model
    def create_scheduled_action(self):
        self.env['ir.cron'].create({
            'name': 'Check No Activity Created Leads for 48 Hours   ',
            'user_id': self.env.user.id,
            'model_id': self.env.ref('crm.model_crm_lead').id,  # The model this cron job will run for
            'state': 'code',
            'code': 'model.check_no_activity_leads()',  # The method to call
            'interval_type': 'days',
            'interval_number': 1,  # Run it every day
            'active': True,
        })


    @api.model
    def write(self, vals):
        if 'stage_id' in vals:
            # Get the new stage and current stage
            new_stage = self.env['crm.stage'].browse(vals['stage_id'])
            current_stage = self.stage_id

            # Check if the user is a salesperson (not an admin)
            if not self.env.user.has_group("ucon_crm_custom_updates.group_ucon_administrative"):
                if new_stage.sequence < current_stage.sequence:
                    raise exceptions.UserError("Salespersons are not allowed to move leads to a previous stage.")



        # if 'stage_id' in vals:
        #         if self.stage_id.name == 'Quote Preperation':
        #             quote = self.env['sale.order'].search([('opportunity_id', '=', self.id)], limit=1)
        #             if quote:
                       
        #                if quote.state != 'sent': 
        #                     if not self.env.user.has_group('base.group_system'):
        #                           raise ValidationError("Access Denied! Please submit the quote before moving the stage.")
        if 'stage_id' in vals:
            
            new_stage = self.env['crm.stage'].browse(vals['stage_id'])

            # Fetch all relevant stages ('New', 'Discovery', 'Quote Preparation')
            discovery_stages = self.env['crm.stage'].search([('name', 'in', ['Quote Submitted'])])

            if discovery_stages:
                max_discovery_sequence = max(discovery_stages.mapped('sequence'))  # Get the highest sequence
             
                if not self.env.user.has_group("ucon_crm_custom_updates.group_ucon_administrative"):
                      for lead in self:
                          # Check if the current stage sequence is within the defined stages
                          if lead.stage_id.sequence < max_discovery_sequence and new_stage.sequence >= max_discovery_sequence:
                              quotation = self.env['sale.order'].search([('opportunity_id', '=', lead.id)],limit=1)
      
                              if not quotation:
                                  raise ValidationError("You cannot move to this stage without creating a quotation.")
      
                              
                              if quotation.state == 'draft':
                                  raise ValidationError("You cannot move to this stage while a quotation is still in draft. Please send the quotation first.")
      
      


        if 'stage_id' in vals:
            new_stage = self.env['crm.stage'].browse(vals['stage_id'])
            
            if new_stage.name == 'Won':
                for record in self:

                        if not record.po_date:
                            raise ValidationError(
                                "The PO Date and PO Ref are required for this lead to be converted to a sale order."
                            )
                        if not record.po_ref:
                              raise ValidationError(
                                "The PO Date and PO Ref are required for this lead to be converted to a sale order."
                            )

        return super(Lead, self).write(vals)
    

    @api.model
    def action_notify_inactive_salespersons(self):
        """Check for salespersons who haven't created an enquiry in 48 hours and send a reminder email."""
        inactivity_threshold = fields.Datetime.now() - timedelta(hours=48)

        # Get all active salespersons with linked users
        salespersons = self.env['hr.employee'].search([('user_id', '!=', False)])

        for salesperson in salespersons:
            last_lead = self.env['crm.lead'].search([
                ('user_id', '=', salesperson.user_id.id),  
                ('create_date', '>=', inactivity_threshold)
            ], order="create_date desc", limit=1)

            _logger.info(f"Processing salesperson: {salesperson.name}, User ID: {salesperson.user_id.id}, Last Lead: {last_lead.id if last_lead else 'None'}")

            if not last_lead:
                self._send_inactivity_email(salesperson)

    def _send_inactivity_email(self, salesperson):
        """Send an email notification for salespersons with no new enquiries in 48 hours."""
        email_template = self.env.ref('ucon_update_r1.alert_email_no_active_enquiry_template_sales_person', raise_if_not_found=False)
        if not email_template:
            _logger.warning("Email template not found: ucon_update_r1.alert_email_no_active_enquiry_template_sales_person")
            return

        # Ensure CRM team exists before accessing
        if salesperson.user_id.sale_team_id and salesperson.user_id.sale_team_id.exists():
            team_lead_email = salesperson.user_id.sale_team_id.user_id.email if salesperson.user_id.sale_team_id.user_id else ""
        else:
            team_lead_email = ""

        _logger.info(f"Checking CRM team for salesperson {salesperson.name} (User ID: {salesperson.user_id.id})")
        _logger.info(f"CRM Team ID: {salesperson.user_id.sale_team_id.id if salesperson.user_id.sale_team_id else 'None'}")
        _logger.info(f"CRM Team Lead: {team_lead_email if team_lead_email else 'None'}")

        if email_template:
            # email_cc = ",".join(filter(None, [
            #     salesperson.user_id.email if salesperson.user_id else "",  # Team Lead
            #     "gm@uconqatar.com"  # GM Email
            # ]))

            email_template.with_context(
                email_to=salesperson.user_id.email  
             ).send_mail(salesperson.user_id.id, force_send=True)

            # _logger.info(f"Email sent to: {salesperson.user_id.email}, CC: {email_cc}")

    
# class MailThread(models.AbstractModel):
#     _inherit = 'mail.thread'

#     @api.model
#     def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
#         """Ensure salesperson is in CC when a client replies to an email."""
        
#         # Call the original message_route to process incoming emails
#         routes = super(MailThread, self).message_route(message, message_dict, model, thread_id, custom_values)

#         # Extract the email details
#         email_from = message_dict.get('email_from')
#         email_to = message_dict.get('to')
#         email_cc = message_dict.get('cc', '')

#         # Search for related Sale Order or CRM Lead (Opportunity) by thread_id
#         related_record = None
#         if model == 'sale.order':
#             related_record = self.env['sale.order'].browse(thread_id)
#         elif model == 'crm.lead':
#             related_record = self.env['crm.lead'].browse(thread_id)

#         # If related record is found and has a salesperson
#         if related_record and related_record.user_id and related_record.user_id.email:
#             salesperson_email = related_record.user_id.email

#             # Ensure the salesperson's email is in CC
#             if salesperson_email not in email_cc:
#                 email_cc += f", {salesperson_email}" if email_cc else salesperson_email
#                 message_dict['cc'] = email_cc  # Update CC in the email

#         return routes  # Return processed email routing data

