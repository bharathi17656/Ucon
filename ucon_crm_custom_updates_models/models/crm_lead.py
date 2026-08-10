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
    po_attachment = fields.Binary(string="PO Attachment", attachment=True)
    po_filename = fields.Char(string="PO File Name")
    po_attachment_ids = fields.Many2many('ir.attachment', 'crm_lead_po_attachment_rel', 'lead_id', 'attachment_id', string="PO Attachments")
    po_amount = fields.Float(string="Partial Amount", compute="_compute_po_and_balance_amounts", store=True)
    balance_amount = fields.Float(string="Balance Amount", compute="_compute_po_and_balance_amounts", store=True)
    is_ucon_admin = fields.Boolean(compute='_compute_is_ucon_admin')

    @api.depends('order_ids', 'order_ids.order_line.cus_po_amount', 'order_ids.order_line.cus_price_subtotal', 'order_ids.order_line.price_subtotal', 'order_ids.date_order', 'order_ids.create_date', 'order_ids.show_amount_fields')
    def _compute_po_and_balance_amounts(self):
        from datetime import datetime
        for lead in self:
            latest_order = lead.order_ids.sorted(key=lambda o: (o.date_order or o.create_date or datetime.min), reverse=True)[:1]
            if latest_order:
                total_po = sum(latest_order.order_line.mapped('cus_po_amount'))
                total_subtotal = sum(latest_order.order_line.mapped('cus_price_subtotal') or latest_order.order_line.mapped('price_subtotal'))
                lead.po_amount = total_po
                lead.balance_amount = max(total_subtotal - total_po, 0.0)
            else:
                lead.po_amount = 0.0
                lead.balance_amount = 0.0

    def _compute_is_ucon_admin(self):
        has_group = self.env.user.has_group('ucon_crm_custom_updates.group_ucon_administrative')
        for lead in self:
            lead.is_ucon_admin = has_group

    @api.onchange("partner_id")
    def _onchange_partner_id_set_user(self):
        """When the partner_id is selected, fetch the related Salesperson (user_id) from res.partner"""
        if not self.env.user.has_group("ucon_crm_custom_updates.group_ucon_administrative"):
            raise exceptions.UserError("You are not have Access to select or add a Customer in lead")
        
        if self.partner_id and self.partner_id.user_id:
            self.user_id = self.partner_id.user_id.id  # Set the salesperson from the selected customer


    def create(self, vals):
        """Set user_id automatically when creating a lead if partner_id is provided"""
        if isinstance(vals, list):
            for val in vals:
                if val.get("partner_id"):
                    partner = self.env["res.partner"].browse(val["partner_id"])
                    if partner.user_id:
                        val["user_id"] = partner.user_id.id
        else:
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

        field_labels = {
            "partner_id": "Customer",
            "email_from": "Email",
            "job_type": "Job Type",
            "phone": "Phone",
            "rfq_number": "RFQ Reference Number",
            "user_id": "Salesperson",
        }

        if "stage_id" in vals:
            new_stage = self.env['crm.stage'].browse(vals['stage_id'])
            if new_stage.name == 'Won':
                sale_order = self.env['sale.order'].search([('opportunity_id', '=', self.id)])
                if sale_order:
                    not_sent_orders = sale_order.filtered(lambda so: so.state not in ['sent', 'sale'])
                    if not_sent_orders:
                        raise ValidationError("Please send the quotation to the customer before moving to 'Won' stage.")
                    else:
                        sale_order.filtered(lambda so: so.state == 'sent').action_confirm()

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

        if "stage_id" in vals:
            for lead in self:
                old_stage = lead.stage_id
                new_stage = self.env["crm.stage"].browse(vals["stage_id"])

                if old_stage.name == "New" and new_stage.name != "New":
                    if not self.env.user.has_group("ucon_crm_custom_updates.group_ucon_administrative"):
                        raise exceptions.UserError("You are not allowed to move a lead from 'New' to another stage.")

                if new_stage.name != "New":
                    missing_fields = []
                    for field in required_fields:
                        val = vals.get(field, getattr(lead, field, False))
                        if not val:
                            missing_fields.append(field_labels.get(field, field))

                    if missing_fields:
                        raise exceptions.UserError(
                            f"First, fill in all mandatory fields before moving to '{new_stage.name}' stage. Missing fields: {', '.join(missing_fields)}"
                        )

        return super(CrmLead, self).write(vals)
