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
        """Open Partial PO Entry Wizard where users can manually add products and set PO amounts."""
        self.ensure_one()
        wizard_lines = []
        for line in self.order_line:
            sor_num = f"{self.po_ref or self.name} - {line.cus_po_amount or line.cus_price_subtotal:,.2f}"
            wizard_lines.append((0, 0, {
                'sor_po_number': sor_num,
                'order_line_id': line.id,
                'product_id': line.product_id.id,
                'cus_po_amount': line.cus_po_amount,
            }))

        wizard = self.env['sale.po.entry.wizard'].create({
            'order_id': self.id,
            'line_ids': wizard_lines,
        })

        return {
            'name': 'PO Amount Entry',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.po.entry.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }


class SalePoEntryWizard(models.TransientModel):
    _name = 'sale.po.entry.wizard'
    _description = 'Sale Order PO Entry Wizard'

    order_id = fields.Many2one('sale.order', string="Quotation", required=True, readonly=True)
    line_ids = fields.One2many('sale.po.entry.wizard.line', 'wizard_id', string="PO Entry Lines")
    order_product_ids = fields.Many2many('product.product', compute='_compute_order_product_ids')

    @api.depends('order_id')
    def _compute_order_product_ids(self):
        for wizard in self:
            wizard.order_product_ids = wizard.order_id.order_line.mapped('product_id')

    def action_confirm_po_entry(self):
        """Apply entered PO Amounts to Sale Order Lines."""
        self.ensure_one()
        self.order_id.write({'show_amount_fields': True})

        for line in self.line_ids:
            target_order_line = line.order_line_id
            if not target_order_line and line.product_id:
                target_order_line = self.order_id.order_line.filtered(lambda l: l.product_id == line.product_id)[:1]

            if target_order_line:
                target_order_line.write({
                    'cus_po_amount': line.cus_po_amount,
                })
                if hasattr(target_order_line, '_onchange_cus_po_amount'):
                    target_order_line._onchange_cus_po_amount()

        if hasattr(self.order_id, '_sync_opportunity_products_and_revenue'):
            self.order_id._sync_opportunity_products_and_revenue()
        if hasattr(self.order_id, '_sync_opportunity_stage'):
            self.order_id._sync_opportunity_stage()

        return {'type': 'ir.actions.act_window_close'}


class SalePoEntryWizardLine(models.TransientModel):
    _name = 'sale.po.entry.wizard.line'
    _description = 'Sale Order PO Entry Wizard Line'

    wizard_id = fields.Many2one('sale.po.entry.wizard', required=True, ondelete='cascade')
    sor_po_number = fields.Char(string="SOR PO Number")
    order_line_id = fields.Many2one('sale.order.line', string="Quotation Line")
    product_id = fields.Many2one('product.product', string="Product", required=True)
    cus_po_amount = fields.Float(string="Po Amount")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and self.wizard_id.order_id:
            matching_line = self.wizard_id.order_id.order_line.filtered(lambda l: l.product_id == self.product_id)[:1]
            if matching_line:
                self.order_line_id = matching_line.id
                self.cus_po_amount = matching_line.cus_po_amount
                self.sor_po_number = f"{self.wizard_id.order_id.po_ref or self.wizard_id.order_id.name} - {matching_line.cus_price_subtotal:,.2f}"

   



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

        return super(SaleOrder, self).write(vals)





class SaleOrderLine(models.Model):
    _inherit='sale.order.line'
    
    order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Order Reference",
        required=True, ondelete='cascade', index=True, copy=False)
    

    
    is_invisible = fields.Boolean(string='Is invisible',default=False)


    cus_po_amount = fields.Float(string='Po Amount', default=0.0, store=True)
    cus_bal_amount = fields.Float(string='Balance Amount', compute='_compute_cus_bal_amount', store=True)
    # price_subtotal = fields.Float(string='PO Amount', compute='_compute_subprice_amount',)
    cus_price_subtotal=fields.Float(string='Total Amount', store=True)







    @api.depends('cus_po_amount', 'cus_price_subtotal')
    def _compute_cus_bal_amount(self):
        """
        Compute the balance amount as cus_total_amount - price_subtotal.
        """
        for line in self:
            line.cus_bal_amount = line.cus_price_subtotal - line.cus_po_amount 

    @api.constrains('price_subtotal', 'cus_po_amount')
    def _check_po_amount(self):
        """
        Ensure that price_subtotal is less than or equal to cus_total_amount.
        """
        for line in self:
            if line.cus_po_amount > line.cus_price_subtotal:
                raise ValidationError(
                    f"The PO Amount {line.cus_po_amount} cannot exceed the Total Amount {line.cus_price_subtotal}."
                )


    
    @api.onchange('cus_price_subtotal')
    def _onchange_cus_price_amount(self):
        for record in self:
            print('record field value',record.order_id.show_amount_fields)
            if record.cus_price_subtotal >= 0:
                    record.price_subtotal=record.cus_price_subtotal
                    record.price_unit=record.cus_price_subtotal


    @api.onchange('cus_po_amount')
    def _onchange_cus_po_amount(self):
        for record in self:
            print('check the line amount', record.cus_po_amount,record.cus_price_subtotal)
            if record.cus_po_amount > record.cus_price_subtotal:
                    raise ValidationError(
                        f"The PO Amount {record.cus_po_amount} cannot exceed the Total Amount {record.cus_price_subtotal}."
                    )
            else:
                print('record field value',record.order_id.show_amount_fields)
                if record.order_id.show_amount_fields == True:
                    print('hello po change')
                    if record.cus_po_amount >= 0:
                        print('record custom po value',record.cus_po_amount)
                        record.price_subtotal=record.cus_po_amount
                        record.price_unit=record.cus_po_amount
                        print('record custom po value',record.price_subtotal,record.price_unit)
