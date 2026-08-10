from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    job_type = fields.Selection([
        ('LEAD', 'LEAD'),
        ('JIH-TRADING', 'JIH-TRADING'),
        ('JIH-FITOUT', 'JIH-FITOUT'),
        ('JIH-PROJECT', 'JIH-PROJECT'),
        ('JIH-MAINTENANCE', 'JIH-MAINTENANCE'),
        ('TENDER', 'TENDER')
    ], string="Job Type")
    product_ids = fields.Many2many('product.template', 'crm_lead_product_template_rel', 'lead_id', 'product_id', string="Products")
    po_date = fields.Date(string="PO Date")
    po_ref = fields.Char(string="PO Reference")
    is_ucon_admin = fields.Boolean(compute='_compute_is_ucon_admin')

    def _compute_is_ucon_admin(self):
        has_group = self.env.user.has_group('ucon_crm_custom_updates.group_ucon_administrative')
        for lead in self:
            lead.is_ucon_admin = has_group


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
        required_fields = [
            "partner_id",
            "email_from",
            "job_type",
            "phone",
            "rfq_number",
            "user_id",
        ]

        fields_being_updated = any(field in vals for field in required_fields)

        if fields_being_updated and "stage_id" not in vals:
            for lead in self:
                if lead.stage_id.name == "New":
                    all_fields_filled = all(
                        bool(vals.get(field, getattr(lead, field, False))) for field in required_fields
                    )
                    if all_fields_filled:
                        discovery_stage = self.env["crm.stage"].search([("name", "=", "Discovery")], limit=1)
                        if discovery_stage:
                            vals["stage_id"] = discovery_stage.id

        return super(CrmLead, self).write(vals)
