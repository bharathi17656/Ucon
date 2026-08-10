from odoo import models, fields, api,exceptions
from odoo.exceptions import ValidationError
from datetime import date,datetime, timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    show_amount_fields = fields.Boolean(string="Show Amount Fields", default=False)



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
                order.opportunity_id.due_days= order.due_days

   



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
                        if not lead.x_studio_po_date:
                            raise ValidationError(
                                "The PO Date and PO Ref are required for this lead to be converted to a sale order."
                            )
                        if not lead.x_studio_po_ref_:
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
               


    @api.onchange('price_subtotal')
    def _onchange_amount(self):
        print("hello")  # Print statement for debugging, can be removed in production
        for record in self:
            # if record.cus_price_subtotal:
            #     # Reset quantity to 1
            #     # record.product_uom_qty = 1

            #     # Set the price unit to match the subtotal
            #     record.price_unit = record.cus_price_subtotal

                # Ensure there is an associated opportunity before setting expected_revenue
                if record.order_id and record.order_id.opportunity_id:
                    print("hai")
                    # Update the expected_revenue on the associated opportunity (CRM lead)
                    record.order_id.opportunity_id.expected_revenue = record.cus_price_subtotal

        
    # @api.onchange('cus_po_amount')
    # def _onchange_po_amount(self):
    #     """
    #     Ensure that price_subtotal is less than or equal to cus_total_amount.
    #     """
       
    
