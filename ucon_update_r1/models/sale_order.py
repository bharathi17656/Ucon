from odoo import models, fields, api,exceptions
from odoo.exceptions import ValidationError
from datetime import datetime

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('state')
    def _onchange_state(self):
        for record in self:
            if record.opportunity_id:  # Check if there is a related opportunity
                # Fetch the mapping based on the current state of the sale order
                mapping = self.env['quotation.stage.mapping'].search(
                    [('sale_order_state', '=', record.state)], limit=1)

                if mapping:
                    # Update the stage of the related opportunity (CRM lead)
                    record.opportunity_id.stage_id = mapping.crm_lead_stage

    def _sync_opportunity_products(self):
        """Automatically populate linked CRM Opportunity x_studio_products from the latest quotation's order lines."""
        for order in self:
            if order.opportunity_id:
                latest_quote = self.env['sale.order'].search([
                    ('opportunity_id', '=', order.opportunity_id.id)
                ], order="create_date desc, id desc", limit=1)
                
                if latest_quote:
                    products = latest_quote.order_line.mapped('product_template_id')
                    order.opportunity_id.write({
                        'x_studio_products': [(6, 0, products.ids)]
                    })

    @api.model_create_multi
    def create(self, vals_list):
        orders = super(SaleOrder, self).create(vals_list)
        orders._sync_opportunity_products()
        return orders

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if 'order_line' in vals or 'opportunity_id' in vals:
            self._sync_opportunity_products()
        return res
                 
    
    # @api.model
    # def write(self, vals):
    #     # Existing code to handle state changes
    #     print('ex------------1',vals)

    #     if 'show_amount_fields' in vals and vals.get('show_amount_fields') == False:
    #         for record in self:
    #             print('its one')
    #             if record.order_line:
    #                 print('its two')
    #                 for i in record.order_line:
    #                     i.cus_po_amount = 0.00
    #                     i.price_subtotal = i.cus_price_subtotal
    #                     i.price_unit = i.cus_price_subtotal
    #                     print('------------------my i', i.price_subtotal, i.cus_po_amount)

                      
                    

    #     if 'state' in vals:
    #         print("this is my state write method")

    #         if vals['state'] == 'sale':

    #             for record in self:
           


    #                 if record.show_amount_fields == True:

    #                     record_expected_revenue=0
    #                     for  revenue in record.order_line:
    #                         record_expected_revenue = record_expected_revenue + revenue.cus_po_amount
                        
    #                     record.opportunity_id.expected_revenue=record_expected_revenue

                        
            

    #                     if record.opportunity_id:
    #                         # Use the opportunity_id record directly
    #                         lead = record.opportunity_id
                    
    #                         print('----------------------browse lead:', lead)
    #                         # record_line=self.env['sale.order.line'].browse({'order_id':record.id})

                            
    #                         # print('this is the record line',record_line)


    #                         if lead:
    #                             # Create a copy of the lead record
                                
    #                         # Fetch the mapping based on the current state of the sale order
    #                             mapping = self.env['quotation.stage.mapping'].search(
    #                                 [('sale_order_state', '=', 'partial')], limit=1)
                                
                               
    #                             print('this is the mapping123',mapping.crm_lead_stage)

    #                             expected_revenue=0

    #                             for  revenue in record.order_line:
    #                                 expected_revenue = expected_revenue + revenue.cus_bal_amount
                                

                                
    #                             copied_lead = lead.copy({
    #                                 'name': lead.name,  # Add a custom name for the copy
    #                                 'expected_revenue':expected_revenue,
    #                                 'stage_id':mapping.crm_lead_stage.id,
                                    

    #                             })


    #                             # mapping_probability = self.env['crm.stage.mapping'].search([('crm_lead_stage', '=', copied_lead.stage_id.id)], limit=1)
            
    #                             # if mapping_probability:
    #                             #     # Update the probability based on the mapping
    #                             #     copied_lead.probability = mapping_probability.probability
                                

    #                             print('---------------Created copy:', copied_lead)

    #                             copied_sale_order = record.copy({
    #                                 'opportunity_id': copied_lead.id,  # Set to the copied lead  
                                     
                                    
    #                             })
                                
                                
                                
    #                             # for  line in copied_sale_order.order_line :
    #                             #     line.price_unit = 0.00
    #                             #     line.price_subtotal = 0.00
    #                             #     line.cus_total_amount=record.order_line.cus_bal_amount


    #                             for i in range(len(copied_sale_order.order_line)):
    #                                 line_data=copied_sale_order.order_line[i]
    #                                 if line_data.price_unit:
    #                                     line_data.price_unit=record.order_line[i].cus_bal_amount
    #                                 if line_data.cus_po_amount:
    #                                     line_data.cus_po_amount=0.00
    #                                 if line_data.cus_price_subtotal:
    #                                     line_data.cus_price_subtotal=record.order_line[i].cus_bal_amount
                                 
                                    



    #         for record in self:
    #             if record.opportunity_id:  # Check if there is a related opportunity
    #                 # Fetch the mapping based on the current state of the sale order
    #                 mapping = self.env['quotation.stage.mapping'].search(
    #                     [('sale_order_state', '=', vals['state'])], limit=1)
                    

    #                 print('this is the mapping',mapping.crm_lead_stage)

    #                 if mapping:
    #                     # Update the stage of the related opportunity (CRM lead)
    #                     record.opportunity_id.stage_id = mapping.crm_lead_stage
    #                     # Optional: You can also log or notify the user if needed
    #                     # record.message_post(body=f'Opportunity stage updated to {mapping.crm_lead_stage.name}.')

                                

                        
                                                            
                            
    #     return super(SaleOrder, self).write(vals)









class EmployeeTarget(models.Model):
    _name = 'hr.employee.target'
    _description = 'Employee Sales and Invoice Targets'

    employee_id = fields.Many2one(comodel_name='hr.employee', string="Employee",  required=True, ondelete='cascade')
    year = fields.Selection([(str(y), str(y)) for y in range(2020, 2035)], string="Year", required=True, default=lambda self: str(fields.Date.today().year))

    # Order Booking Fields
    order_booking_target = fields.Float(string="Order Booking Target")
    order_booking_achieved = fields.Float(string="Order Booking Achieved", compute="_compute_order_booking_achieved", store=False)
    order_booking_percentage = fields.Float(string="Order Booking %", compute="_compute_order_booking_percentage", store=True)

    # Invoice Fields
    invoice_target = fields.Float(string="Invoice Target")
    invoice_achieved = fields.Float(string="Invoice Achieved")  # Manual Entry
    invoice_percentage = fields.Float(string="Invoice %", compute="_compute_invoice_percentage", store=True)

    

    @api.depends('order_booking_target', 'order_booking_achieved')
    def _compute_order_booking_percentage(self):
        for record in self:
            if record.order_booking_target:
                record.order_booking_percentage = (record.order_booking_achieved / record.order_booking_target) * 100
            else:
                record.order_booking_percentage = 0.0


    @api.depends('invoice_target', 'invoice_achieved')
    def _compute_invoice_percentage(self):
        for record in self:
            if record.invoice_target:
                record.invoice_percentage = (record.invoice_achieved / record.invoice_target) * 100
            else:
                record.invoice_percentage = 0.0



    @api.depends('employee_id', 'year')
    def _compute_order_booking_achieved(self):
        for record in self:
            if record.employee_id and record.year:
                start_date = f"{record.year}-01-01"
                end_date = f"{record.year}-12-31"

                sales_orders = self.env['sale.order'].search([
                    ('user_id', '=', record.employee_id.user_id.id),
                    ('date_order', '>=', datetime.strptime(start_date, "%Y-%m-%d")),
                    ('date_order', '<=', datetime.strptime(end_date, "%Y-%m-%d")),
                    ('state', 'in', ['sale', 'done'])  # Only confirmed orders
                ])

                record.order_booking_achieved = sum(sales_orders.mapped('amount_total'))
            else:
                record.order_booking_achieved = 0.0

    # write and create do not need manual _compute_order_booking_achieved calls for non-stored compute fields

    





class Employee(models.Model):
    _inherit = 'hr.employee'

    target_ids = fields.One2many(
        comodel_name='hr.employee.target',
        inverse_name='employee_id',
        string="Targets"
    )


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(SaleOrderLine, self).create(vals_list)
        lines.mapped('order_id')._sync_opportunity_products()
        return lines

    def write(self, vals):
        res = super(SaleOrderLine, self).write(vals)
        if any(field in vals for field in ['product_id', 'product_template_id', 'order_id']):
            self.mapped('order_id')._sync_opportunity_products()
        return res

    def unlink(self):
        orders = self.mapped('order_id')
        res = super(SaleOrderLine, self).unlink()
        orders._sync_opportunity_products()
        return res

