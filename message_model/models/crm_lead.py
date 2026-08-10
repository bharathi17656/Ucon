from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    is_read_all = fields.Boolean(
        string="All Messages Read",
        store=True
    )

    new_messages = fields.Integer(
        string="New Messages",
        store=True,
        default=0
    )

    last_viewed_date = fields.Datetime(
        string="Last Viewed Date",
        default=fields.Datetime.now
    )

    # def _compute_message_unread(self):
    #     """Updates last visited timestamp"""
    #     for lead in self:
    #         lead.last_viewed_date = fields.Datetime.now()
    #         lead.new_messages = 0
    #         lead.is_read_all = False  # True if no new messages


    def remove_unwanted_followers(self):
        for record in self:
            print(f"Removing all followers from {record._name} - ID: {record.id}")

            

            unsubscribe_followers = [
                follower.partner_id.id
                for follower in record.message_follower_ids
            ]  # ✅ Get all followers' IDs

            if unsubscribe_followers:
                print(f"Unfollowing in {record._name}: {unsubscribe_followers}")
                record.message_unsubscribe(unsubscribe_followers)  # ✅ Remove all followers

            sale = self.env['sale.order'].search([('opportunity_id', '=', record.id)], limit=1)  # ✅ Use limit=1 for efficiency
            if sale:
                print(f"Removing followers from linked Sale Order - ID: {sale.id}")

                sale_unsubscribe_followers = [
                    follower.partner_id.id
                    for follower in sale.message_follower_ids
                ]  # ✅ Get followers for Sale Order

                if sale_unsubscribe_followers:
                    print(f"Unfollowing in {sale._name}: {sale_unsubscribe_followers}")
                    sale.message_unsubscribe(sale_unsubscribe_followers)  # ✅ Remove all followers from Sale Order
                
                


    def _action_view_lead(self):
        """ Update last_viewed_date only when a lead is viewed explicitly """
        for lead in self:
            lead.last_viewed_date = fields.Datetime.now()
            lead.remove_unwanted_followers()
            # sale_lead = self.env['sale.order'].search([('opportunity_id', '=', lead.id)])
            # self.check_message_count_auto()
            _logger.info(f"Lead {lead.id} viewed. Updated last_viewed_date: {lead.last_viewed_date} and the new message count is {lead.new_messages}")

    def read(self, fields=None, load='_classic_read'):
        """ Override read method to detect when a lead is opened """
        result = super(CrmLead, self).read(fields, load)

        if self.env.context.get('tracking_disable'):
            return result  # Skip updating if tracking is disabled

        if 'last_viewed_date' in fields:
            self._action_view_lead()
            self.own_check_message_count_auto()

        return result


    def check_message_count_auto(self):
        """Check unread messages for all leads"""
        print("Checking unread messages...")
        unread_notifications=[]
        sale_unread_notifications=[]
        leads = self.search([])

        for lead in leads:
            if not lead.last_viewed_date:
                print("Updating last viewed date")
                lead.last_viewed_date = fields.Datetime.now()

            print(f"Lead {lead.id}, Last Viewed: {lead.last_viewed_date}")

            unread_notifications = self.env['mail.message'].search([
                ('res_id', '=', lead.id),
                ('model', '=', 'crm.lead'),
                ('date', '>=', lead.last_viewed_date),
                ('message_type','=','comment')
            ])

            sale_lead = self.env['sale.order'].search([('opportunity_id', '=', lead.id)])

            for sale in sale_lead:
                if not sale.last_viewed_date:
                    print("Updating last viewed date")
                    sale.last_viewed_date = fields.Datetime.now()

                sale_unread_notifications = self.env['mail.message'].search([
                    ('res_id', '=', sale.id),
                    ('model', '=', 'sale.order'),
                    ('date', '>=', sale.last_viewed_date),
                     ('message_type','=','comment')
                ])

                _logger.info(f" ID: {lead.id} Unread messages: {len(unread_notifications)} (CRM), id:{sale.id} {len(sale_unread_notifications)} (Sales)")

            lead.new_messages = len(unread_notifications) + len(sale_unread_notifications)
            lead.is_read_all = lead.new_messages == 0
            _logger.info(f" id: {lead.id} Lead Unread messages count {lead.new_messages} and Lead is read {lead.is_read_all}")


   

    def own_check_message_count_auto(self):
        """Check unread messages for all leads"""
        print("Checking unread messages...")
        unread_notifications=[]
        sale_unread_notifications=[]
        # leads = self.search([])

        for lead in self:
            if not lead.last_viewed_date:
                print("Updating last viewed date")
                lead.last_viewed_date = fields.Datetime.now()

            print(f"Lead {lead.id}, Last Viewed: {lead.last_viewed_date}")

            unread_notifications = self.env['mail.message'].search([
                ('res_id', '=', lead.id),
                ('model', '=', 'crm.lead'),
                ('date', '>=', lead.last_viewed_date),
                ('message_type','=','comment')
            ])

            sale_lead = self.env['sale.order'].search([('opportunity_id', '=', lead.id)])

            for sale in sale_lead:
                if not sale.last_viewed_date:
                    print("Updating last viewed date")
                    sale.last_viewed_date = fields.Datetime.now()

                sale_unread_notifications = self.env['mail.message'].search([
                    ('res_id', '=', sale.id),
                    ('model', '=', 'sale.order'),
                    ('date', '>=', sale.last_viewed_date),
                     ('message_type','=','comment')
                ])

                _logger.info(f" ID: {lead.id} Unread messages: {len(unread_notifications)} (CRM), id:{sale.id} {len(sale_unread_notifications)} (Sales)")

            lead.new_messages = len(unread_notifications) + len(sale_unread_notifications)
            lead.is_read_all = lead.new_messages == 0
            _logger.info(f" id: {lead.id} Lead Unread messages count {lead.new_messages} and Lead is read {lead.is_read_all}")


   


    
    @api.model
    def auto_remove_all_followers(self):
        """Scheduled action to remove all followers from CRM Leads & Sales Orders"""

        models_to_clean = ['crm.lead', 'sale.order']  # ✅ Clean followers in both models

        for model_name in models_to_clean:
            records = self.env[model_name].search([])  # ✅ Get all records of the model

            for record in records:
                print(f"Removing all followers in {model_name} - ID: {record.id}")

                unsubscribe_followers = [
                    follower.partner_id.id
                    for follower in record.message_follower_ids
                ]  # ✅ Get all followers' IDs

                if unsubscribe_followers:
                    print(f"Unfollowing in {model_name}: {unsubscribe_followers}")
                    record.message_unsubscribe(unsubscribe_followers)  # ✅ Remove all followers

  



class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # is_read_all = fields.Boolean(
    #     string="All Messages Read",
    #     compute="_compute_message_unread",
    #     store=True
    # )

    new_messages = fields.Integer(
        string="New Messages",
        store=True,
        default=0
    )

    last_viewed_date = fields.Datetime(
        string="Last Viewed Date",
        default=fields.Datetime.now
    )

    # def compute_message_unread(self):
    #     """Updates last visited timestamp"""
    #     for order in self:
    #         order.last_viewed_date = fields.Datetime.now()
    #         order.new_messages = 0
    #         order.is_read_all = False  # True if no new messages

    def _action_view_lead(self):
        """ Update last_viewed_date only when a lead is viewed explicitly """
        for order in self:
            order.last_viewed_date = fields.Datetime.now()
            # order.new_messages = 0
          
            _logger.info(f"Order {order.id} viewed. Updated last_viewed_date: {order.last_viewed_date}")

    def read(self, fields=None, load='_classic_read'):
        """ Override read method to detect when an order is opened """
        result = super(SaleOrder, self).read(fields, load)

        if self.env.context.get('tracking_disable'):
            return result  # Skip updating if tracking is disabled

        if 'last_viewed_date' in fields:
            self._action_view_lead()
            for lead in self:
                if lead.opportunity_id:
                    lead.opportunity_id.own_check_message_count_auto()

        return result

