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
