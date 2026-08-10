from odoo import models, fields, api
from odoo import exceptions
from odoo.exceptions import ValidationError

class CrmLead(models.Model):
    _inherit = "crm.lead"


    cash_purchased = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Cash Purchased",
        default="no",
        required=True
    )
    x_studio_job_type = fields.Selection([
        ('LEAD', 'LEAD'),
        ('JIH-TRADING', 'JIH-TRADING'),
        ('JIH-FITOUT', 'JIH-FITOUT'),
        ('JIH-PROJECT', 'JIH-PROJECT'),
        ('JIH-MAINTENANCE', 'JIH-MAINTENANCE'),
        ('TENDER', 'TENDER')
    ], string="Job Type")
    x_studio_products = fields.Many2many('product.template', 'crm_lead_product_template_rel', 'lead_id', 'product_id', string="Products")

    @api.onchange("partner_id")
    def _onchange_partner_id_set_user(self):
        """When the partner_id is selected, fetch the related Salesperson (user_id) from res.partner"""
        if not self.env.user.has_group("ucon_crm_custom_updates.group_ucon_administrative"):
                raise exceptions.UserError("You are not have Access to select or add a Customer in lead")
        
        if self.partner_id and self.partner_id.user_id:
            self.user_id = self.partner_id.user_id.id  # Set the salesperson from the selected customer
   


    def create(self, vals):
        """Set user_id automatically when creating a lead if partner_id is provided"""
        
        # Handle case where vals is a list of dictionaries
        if isinstance(vals, list):
            for val in vals:
                if val.get("partner_id"):
                    partner = self.env["res.partner"].browse(val["partner_id"])
                    if partner.user_id:
                        val["user_id"] = partner.user_id.id
        else:  # Handle single dictionary case
            if vals.get("partner_id"):
                partner = self.env["res.partner"].browse(vals["partner_id"])
                if partner.user_id:
                    vals["user_id"] = partner.user_id.id
    
        return super(CrmLead, self).create(vals)




    def write(self, vals):
            # Define the fields to check
            required_fields = [
                "partner_id",
                "email_from",
                "x_studio_job_type",
                "phone",
                "rfq_number",
                "user_id",
                "x_studio_products",
            ]
    
            # Check if any of these fields are in vals (i.e., being updated)
            fields_being_updated = any(field in vals for field in required_fields)
            if "stage_id" in vals:
                    won_stage = self.env['crm.stage'].browse(vals['stage_id']).name == 'Won'
                    if won_stage:
                        sale_order = self.env['sale.order'].search([('opportunity_id', '=', self.id)])
                        if sale_order:
                            not_sent_orders = sale_order.filtered(lambda so: so.state not in ['sent', 'sale'])
                            if not_sent_orders:
                                raise ValidationError("Please send the quotation to the customer before moving to 'Won' stage.")
                            else:
                                sale_order.filtered(lambda so: so.state == 'sent').action_confirm()
                        
                        
                    
            if fields_being_updated:
                for lead in self:
                    # Ensure all required fields have values
                    all_fields_filled = all(
                        bool(vals.get(field, lead[field])) for field in required_fields
                    )
    
                    # If all fields are filled, move to "Discovery" stage
                    if all_fields_filled:
                        discovery_stage = self.env["crm.stage"].search([("name", "=", "Discovery")], limit=1)
                        if discovery_stage:
                            vals["stage_id"] = discovery_stage.id  # Move to Discovery stage
                            
            if "stage_id" in vals:
                for lead in self:
                    # Get current stage (before update)
                    old_stage = lead.stage_id
                    # Get new stage (after update)
                    new_stage = self.env["crm.stage"].browse(vals["stage_id"])
    
                    # If moving from "New" to another stage, check the group
                    if old_stage.name == "New" and new_stage.name != "New":
                        if not self.env.user.has_group("ucon_crm_custom_updates.group_ucon_administrative"):
                             raise exceptions.UserError("You are not allowed to move a lead from 'New' to another stage.")

                 
     
                        all_fields_filled = all(
                            bool(vals.get(field, getattr(lead, field, False))) for field in required_fields
                        )
                        if not all_fields_filled:
                            raise exceptions.UserError("First, fill in all the mandatory fields of this lead. Only then can you move to the next stage.")
                                     
            return super(CrmLead, self).write(vals)
