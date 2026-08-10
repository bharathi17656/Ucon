from odoo import models, fields, api,exceptions
from odoo.exceptions import ValidationError
from datetime import date,datetime, timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    show_amount_fields = fields.Boolean(string="Partial Released", default=False)



    due_days = fields.Integer(
        string="Days Due",
        compute="_compute_due_days",
        store=True,
        compute_sudo=True
    )

    @api.depends('date_order')
    def _compute_due_days(self):
        today = date.today()
        for order in self:
            if order.date_order:
                due_days = ( today - order.date_order.date()).days
                order.due_days = max(due_days, 0)  # Ensure no negative values
                order.opportunity_id.due_days= order.due_days
            else:
                order.due_days = 0
    def action_open_po_entry_wizard(self):
        """Open PO Amount Entry editable list view popup."""
        self.ensure_one()
        wizard = self.env['sale.po.entry.wizard'].search([('order_id', '=', self.id)], limit=1)
        if not wizard:
            wizard = self.env['sale.po.entry.wizard'].create({
                'order_id': self.id,
            })

        view_id = self.env.ref('crm_custom_updates.view_sale_po_entry_wizard_line_tree').id
        return {
            'name': 'PO Amount Entry',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.po.entry.wizard.line',
            'view_mode': 'list',
            'views': [(view_id, 'list')],
            'domain': [('wizard_id', '=', wizard.id)],
            'target': 'new',
            'context': {
                'default_wizard_id': wizard.id,
                'allowed_product_ids': self.order_line.mapped('product_id').ids,
                'opportunity_id': self.opportunity_id.id if self.opportunity_id else False,
            }
        }


class SalePoEntryWizard(models.TransientModel):
    _name = 'sale.po.entry.wizard'
    _description = 'Sale Order PO Entry Wizard'

    order_id = fields.Many2one('sale.order', string="Quotation", required=True, readonly=True)
    line_ids = fields.One2many('sale.po.entry.wizard.line', 'wizard_id', string="PO Entry Lines")

    def _sync_po_amounts(self):
        for wizard in self:
            if wizard.order_id:
                order = wizard.order_id
                order.write({'show_amount_fields': True})
                for line in order.order_line:
                    matching_wiz_lines = wizard.line_ids.filtered(
                        lambda w: (w.order_line_id and w.order_line_id == line) or (w.product_id and w.product_id == line.product_id)
                    )
                    total_po = sum(matching_wiz_lines.mapped('cus_po_amount'))
                    line.write({'cus_po_amount': total_po})
                    if hasattr(line, '_onchange_cus_po_amount'):
                        line._onchange_cus_po_amount()
                if hasattr(order, '_sync_opportunity_products_and_revenue'):
                    order._sync_opportunity_products_and_revenue()
                if hasattr(order, '_sync_opportunity_stage'):
                    order._sync_opportunity_stage()


class SalePoEntryWizardLine(models.TransientModel):
    _name = 'sale.po.entry.wizard.line'
    _description = 'Sale Order PO Entry Wizard Line'

    wizard_id = fields.Many2one('sale.po.entry.wizard', required=True, ondelete='cascade')
    sor_po_number = fields.Char(string="SOR PO Number")
    order_line_id = fields.Many2one('sale.order.line', string="Quotation Line")
    product_id = fields.Many2one('product.product', string="Product", required=True)
    cus_po_amount = fields.Float(string="Po Amount")

    @api.constrains('cus_po_amount', 'product_id', 'order_line_id')
    def _check_wizard_po_amount(self):
        for rec in self:
            if rec.wizard_id and rec.wizard_id.order_id and rec.product_id:
                order = rec.wizard_id.order_id
                target_line = rec.order_line_id or order.order_line.filtered(lambda l: l.product_id == rec.product_id)[:1]
                if target_line:
                    matching_wiz_lines = rec.wizard_id.line_ids.filtered(
                        lambda w: (w.order_line_id and w.order_line_id == target_line) or (w.product_id and w.product_id == rec.product_id)
                    )
                    total_wiz_po = sum(matching_wiz_lines.mapped('cus_po_amount'))
                    max_allowed = target_line.cus_price_subtotal or target_line.price_subtotal
                    if max_allowed and total_wiz_po > max_allowed:
                        raise ValidationError(
                            f"The total PO Amount ({total_wiz_po:.2f}) for product '{rec.product_id.name}' exceeds its Total Amount ({max_allowed:.2f})."
                        )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and self.wizard_id.order_id:
            matching_line = self.wizard_id.order_id.order_line.filtered(lambda l: l.product_id == self.product_id)[:1]
            if matching_line:
                self.order_line_id = matching_line.id
                order = self.wizard_id.order_id
                po_ref_val = getattr(order, 'po_ref', False) or (order and order.opportunity_id and getattr(order.opportunity_id, 'po_ref', False)) or order.name
                self.sor_po_number = f"{po_ref_val} - {(matching_line.cus_price_subtotal or matching_line.price_subtotal):,.2f}"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._apply_po_amount()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._apply_po_amount()
        return res

    def unlink(self):
        wizards = self.mapped('wizard_id')
        res = super().unlink()
        for wizard in wizards:
            wizard._sync_po_amounts()
        return res

    def _apply_po_amount(self):
        wizards = self.mapped('wizard_id')
        for wizard in wizards:
            wizard._sync_po_amounts()

   



    def _compute_due_days_she(self):
        today = date.today()
        orders = self.env['sale.order'].search([('date_order', '!=', False)])  # Fetch only relevant records

        for order in orders:
            due_days = ( today - order.date_order.date()).days
            order.write({'due_days': max(due_days, 0)})  # Ensure no negative values
            order.opportunity_id.due_days= order.due_days




    @api.constrains('opportunity_id')
    def _check_unique_opportunity_id(self):
        for record in self:
            # Check if opportunity_id is not empty or null
            if record.opportunity_id:
                # Ensure opportunity_id is unique (check all other sale orders except the current one)
                existing_orders = self.search([('opportunity_id', '=', record.opportunity_id.id), ('id', '!=', record.id)])
                if existing_orders:
                    raise ValidationError(f"{record.opportunity_id.name} is already associated with another sale order or quotation.")



    @api.onchange('state')
    def _onchange_state(self):
        print("-----------this is my onchange state")
        for record in self:
            if record.opportunity_id:  # Check if there is a related opportunity
                # Fetch the mapping based on the current state of the sale order
                mapping = self.env['quotation.stage.mapping'].search(
                    [('sale_order_state', '=', record.state)], limit=1)
                


                if mapping:
                    # Update the stage of the related opportunity (CRM lead)
                    record.opportunity_id.stage_id = mapping.crm_lead_stage
                    # You can also log or notify the user if needed
                    # record.message_post(body=f'Opportunity stage updated to {mapping.crm_lead_stage.name}.')

            # if record.opportunity_id 

    

    @api.model
    def write(self, vals):
        # Existing code to handle state changes
        print('ex------------1',vals)

        if 'show_amount_fields' in vals and vals.get('show_amount_fields') == False:
            for record in self:
                print('its one')
                if record.order_line:
                    print('its two')
                    for i in record.order_line:
                        i.cus_po_amount = 0.00
                        i.price_subtotal = i.cus_price_subtotal
                        i.price_unit = i.cus_price_subtotal
                        print('------------------my i', i.price_subtotal, i.cus_po_amount)

                      
                    

        if 'state' in vals:
            print("this is my state write method")

            if vals['state'] == 'sale':
                for record in self:
                    if record.opportunity_id:
                        # Use the opportunity_id record directly
                        lead = record.opportunity_id
                        if not lead.po_date:
                            raise ValidationError(
                                "The PO Date and PO Ref are required for this lead to be converted to a sale order."
                            )
                        if not lead.po_ref:
                              raise ValidationError(
                                "The PO Date and PO Ref are required for this lead to be converted to a sale order."
                            )

                for record in self:
                    if record.show_amount_fields:
                        record_expected_revenue = sum(revenue.cus_po_amount for revenue in record.order_line)
                        if record.opportunity_id:
                            record.opportunity_id.expected_revenue = record_expected_revenue

                        if record.opportunity_id:
                            lead = record.opportunity_id
                            if lead:
                                mapping = self.env['quotation.stage.mapping'].search(
                                    [('sale_order_state', '=', 'partial')], limit=1)
                                expected_revenue = sum(revenue.cus_bal_amount for revenue in record.order_line)

                                copied_lead = lead.copy({
                                    'name': lead.name,
                                    'expected_revenue': expected_revenue,
                                    'stage_id': mapping.crm_lead_stage.id if mapping else lead.stage_id.id,
                                })

                                copied_sale_order = record.copy({
                                    'opportunity_id': copied_lead.id,
                                })

                                for i in range(len(copied_sale_order.order_line)):
                                    line_data = copied_sale_order.order_line[i]
                                    if line_data.price_unit:
                                        line_data.price_unit = record.order_line[i].cus_bal_amount
                                    if line_data.cus_po_amount:
                                        line_data.cus_po_amount = 0.00
                                    if line_data.cus_price_subtotal:
                                        line_data.cus_price_subtotal = record.order_line[i].cus_bal_amount

                                copy_expected_revenue = sum(
                                    record.order_line[i].cus_bal_amount for i in range(len(copied_sale_order.order_line))
                                    if copied_sale_order.order_line[i].cus_price_subtotal
                                )
                                copied_lead.expected_revenue = copy_expected_revenue

            for record in self:
                if record.opportunity_id:
                    mapping = self.env['quotation.stage.mapping'].search(
                        [('sale_order_state', '=', vals['state'])], limit=1)
                    if mapping:
                        record.opportunity_id.stage_id = mapping.crm_lead_stage

        return super().write(vals)





class SaleOrderLine(models.Model):
    _inherit='sale.order.line'
    
    order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Order Reference",
        required=True, ondelete='cascade', index=True, copy=False)
    

    
    is_invisible = fields.Boolean(string='Is invisible',default=False)

    def action_open_po_entry_wizard(self):
        """Open PO Amount Entry editable list view popup from sale order line control button."""
        order = self.order_id
        if not order:
            active_id = self.env.context.get('active_id') or self.env.context.get('default_order_id')
            if active_id:
                order = self.env['sale.order'].browse(active_id)
        if not order and self:
            order = self[0].order_id

        if order:
            return order.action_open_po_entry_wizard()
        return True


    cus_po_amount = fields.Float(string='Po Amount', default=0.0, store=True)
    cus_bal_amount = fields.Float(string='Balance Amount', compute='_compute_cus_bal_amount', store=True)
    cus_price_subtotal = fields.Float(string='Total Amount', compute='_compute_cus_price_subtotal', store=True, readonly=False)

    @api.depends('price_subtotal')
    def _compute_cus_price_subtotal(self):
        for line in self:
            line.cus_price_subtotal = line.price_subtotal







    @api.depends('cus_po_amount', 'cus_price_subtotal')
    def _compute_cus_bal_amount(self):
        """
        Compute the balance amount as cus_total_amount - price_subtotal.
        """
        for line in self:
            line.cus_bal_amount = line.cus_price_subtotal - line.cus_po_amount 

    @api.constrains('price_subtotal', 'cus_price_subtotal', 'cus_po_amount')
    def _check_po_amount(self):
        """
        Ensure that PO Amount cannot exceed Total Amount.
        """
        for line in self:
            max_allowed = line.cus_price_subtotal or line.price_subtotal
            if max_allowed and line.cus_po_amount > max_allowed:
                raise ValidationError(
                    f"The PO Amount ({line.cus_po_amount:.2f}) cannot exceed the Total Amount ({max_allowed:.2f})."
                )

    @api.onchange('cus_po_amount')
    def _onchange_cus_po_amount(self):
        for record in self:
            max_allowed = record.cus_price_subtotal or record.price_subtotal
            if max_allowed and record.cus_po_amount > max_allowed:
                raise ValidationError(
                    f"The PO Amount ({record.cus_po_amount:.2f}) cannot exceed the Total Amount ({max_allowed:.2f})."
                )
