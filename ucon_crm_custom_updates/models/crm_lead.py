from odoo import models, fields, api,exceptions
from odoo.exceptions import ValidationError

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    x_studio_job_type = fields.Selection([
        ('LEAD', 'LEAD'),
        ('JIH-TRADING', 'JIH-TRADING'),
        ('JIH-FITOUT', 'JIH-FITOUT'),
        ('JIH-PROJECT', 'JIH-PROJECT'),
        ('JIH-MAINTENANCE', 'JIH-MAINTENANCE'),
        ('TENDER', 'TENDER')
    ], string="Job Type")
    x_studio_products = fields.Many2many('crm.tag', 'crm_lead_studio_products_rel', 'lead_id', 'tag_id', string="Products")


    @api.onchange("partner_id")
    def _onchange_partner_id_set_user(self):
            """When the partner_id is selected, fetch the related Salesperson (user_id) from res.partner"""
            if self.partner_id and self.partner_id.user_id:
                self.user_id = self.partner_id.user_id.id  # Set the salesperson from the selected customer




    def create(self, vals):
        """Set user_id automatically when creating a lead if partner_id is provided"""
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

        return super(CrmLead, self).write(vals)
