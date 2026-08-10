from odoo import models, fields, api,exceptions
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class Lead(models.Model):
    _inherit = 'crm.lead'


    probability = fields.Float(default=0.0, string="Probability")

      
    due_days = fields.Integer(
        string="Days Due",
        store=True,
        compute_sudo=True
    )



    # def sent_stage_quotation(self,res_id):
    #     sale_order = self.env['sale.order'].browse(res_id)
    #     if not sale_order:
    #         raise ValidationError("Sale Order not found.")

    #     return sale_order.state

    def sent_stage_quotation(self,res_id,res_model):
        if res_model == 'crm.lead':
            lead=self.env['crm.lead'].browse(res_id)
            if lead.stage_id.name in ['Discovery','Quote Preperation']:
                sale_order=self.env['sale.order'].search([('opportunity_id','=',lead.id)])
                if not sale_order:
                    return 'Not Available'
               
                return sale_order.state
            return 'Not Available'
                    
        if res_model == 'sale.order':
            sale_order = self.env['sale.order'].browse(res_id)
            if not sale_order:
                raise ValidationError("Sale Order not found.")

            return sale_order.state
        
    @api.model
    def quotation_stage_update(self, message_id):
        """
        Update Sale Order state to 'sent' and map related CRM Lead (Opportunity) stage.
        """
        if not message_id:
            raise ValidationError("Message ID is required.")

        # Get the mail message
        message = self.env['mail.message'].browse(message_id)
        if not message or not message.res_id:
            raise ValidationError("Invalid message or no related record found.")

        # Ensure the message is linked to Sale Order or CRM Lead
        if message.model not in ["sale.order", "crm.lead"]:
            raise ValidationError("This message is not related to a Sale Order or CRM Lead.")

        updated = False  # Track if an update was performed

        if message.model == "sale.order":
            sale_order = self.env['sale.order'].browse(message.res_id)
            if not sale_order:
                raise ValidationError("Sale Order not found.")

            # Update Sale Order state to 'sent' if it's in draft
            if sale_order.state == 'draft':
                sale_order.write({'state': 'sent'})
                updated = True

            # Update related CRM Lead stage if mapping exists
            if sale_order.opportunity_id:
                mapping = self.env['quotation.stage.mapping'].search(
                    [('sale_order_state', '=', sale_order.state)], limit=1
                )
                if mapping and sale_order.opportunity_id.stage_id != mapping.crm_lead_stage:
                    sale_order.opportunity_id.stage_id = mapping.crm_lead_stage
                    updated = True

        if message.model == "crm.lead":
            lead = self.env['crm.lead'].browse(message.res_id)
            if not lead:
                raise ValidationError("Lead not found.")

            sale_order = self.env['sale.order'].search([('opportunity_id', '=', lead.id)], limit=1)
            if sale_order and sale_order.state == 'draft':
                sale_order.write({'state': 'sent'})
                updated = True

                if sale_order.opportunity_id:
                    mapping = self.env['quotation.stage.mapping'].search(
                        [('sale_order_state', '=', sale_order.state)], limit=1
                    )
                    if mapping and sale_order.opportunity_id.stage_id != mapping.crm_lead_stage:
                        sale_order.opportunity_id.stage_id = mapping.crm_lead_stage
                        updated = True

        return "Update Successful" if updated else "No changes made"


    # @api.onchange('stage_id')
    # def _check_stage_change(self):
    #     _logger.info(f"Lead ID {self.id} trying to move from {self.stage_id.name} to {self.stage_id.name} quotation {sale_order}")
    #     # Fetch all CRM stages ordered by sequence
    #     all_stages = self.env['crm.stage'].search([], order="sequence asc")
        
    #     # Find the 'Quote Submitted' stage
    #     quote_submitted_stage = all_stages.filtered(lambda s: s.name == 'Quote Submitted')
        
    #     if not quote_submitted_stage:
    #         return  # If 'Quote Submitted' stage is not found, don't apply validation

    #     # Get stages with a sequence greater than or equal to 'Quote Submitted'
    #     next_stages = all_stages.filtered(lambda s: s.sequence >= quote_submitted_stage.sequence)

    #     # Check if the stage is moving to 'Quote Submitted' or beyond
    #     if self.stage_id and self.stage_id in next_stages:
            
    #         sale_order=self.env['sale.order'].search([('opportunity_id','in',[self.id])],limit=1)
    #         _logger.info(f"Lead ID {self.id} trying to move from {self.stage_id.name} to {self.stage_id.name} quotation {sale_order}")
            
    #         if not sale_order:
    #             raise ValidationError("Access Denied! No related quotation found. Please create and submit a quote before proceeding.")

    #         if sale_order.state == 'draft':                                   
    #             raise ValidationError("Access Denied! Please submit the quote before moving the stage.")

    
    # def quotation_stage_update(self, message_id):
    #     """
    #     Update Sale Order state to 'sent' and map related CRM Lead (Opportunity) stage.
    #     """
    #     if not message_id:
    #         raise ValidationError("Message ID is required.")

    #     # Get the mail message
    #     message = self.env['mail.message'].browse(message_id)
    #     if not message or not message.res_id:
    #         raise ValidationError("Invalid message or no related record found.")

    #     # Ensure the message is linked to a Sale Order
    #     if message.model != "sale.order":
    #         raise ValidationError("This message is not related to a Sale Order.")

    #     # Fetch the Sale Order
    #     sale_order = self.env['sale.order'].browse(message.res_id)
    #     if not sale_order:
    #         raise ValidationError("Sale Order not found.")

    #     # Update Sale Order state to 'sent'
    #     sale_order.write({'state': 'sent'})

    #     # If the Sale Order has a related Opportunity (CRM Lead)
    #     if sale_order.opportunity_id:
    #         # Fetch the stage mapping based on the updated Sale Order state
    #         mapping = self.env['quotation.stage.mapping'].search(
    #             [('sale_order_state', '=', sale_order.state)], limit=1
    #         )

    #         if mapping:
    #             # ✅ Update the stage of the related CRM Lead
    #             sale_order.opportunity_id.stage_id = mapping.crm_lead_stage

    #     return "Success"



    @api.onchange('name')
    def _custom_name(self):
        if self.name:  # Ensure the field has a value before trying to modify it
            self.name = self.name.upper()

    @api.onchange('team_id')
    def _team_id_onchange(self):
        if self.stage_id == 1:
            self.probability = 0.00

    @api.onchange('partner_id')
    def _custom_name(self):
        if self.partner_id:  # Ensure the field has a value before trying to modify it
            self.partner_id.name = self.partner_id.name.upper()


    

class CustomCrmLead(models.Model):
    _inherit = 'project.project'

    @api.onchange('name')
    def _custom_name(self):
        if self.name:  # Ensure the field has a value before trying to modify it
            self.name = self.name.upper()



class ResPartner(models.Model):
    _inherit = 'res.partner'  

    @api.onchange('name')
    def _custom_name(self):
        if self.name:  # Ensure the field has a value before trying to modify it
            self.name = self.name.upper()
    





