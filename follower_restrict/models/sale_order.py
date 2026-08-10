
from odoo import models,api,fields


class SaleOrder(models.Model):
    """Inherits the sale order for disable the follower"""
    _inherit = 'sale.order'

    remove_follower=fields.Boolean(compute='_compute_remove_unwanted_followers', store=True)

    # def action_confirm(self):
    #     """Check whether 'Disable Follower' is enabled.
    #         Check whether user and customer are same.
    #         If not unsubscribe the customer from followers list"""
    #     result = super(SaleOrder, self).action_confirm()
    #     if self.env['ir.config_parameter'].get_param(
    #             "follower_restrict.disable_followers"):
    #         user_partner = self.user_id.partner_id.id if self.user_id else False
    #         unsubscribe_followers = [follower.partner_id.id for follower in
    #                                  self.message_follower_ids if
    #                                  follower.partner_id.id != user_partner]
    #         if unsubscribe_followers:
    #             self.message_unsubscribe(unsubscribe_followers)
    #     return result
    



    @api.model
    def write(self, vals):
        """Ensure that no new followers are added when updating"""

        print("hello word----------------------->its follower_restrict")
        result = super(SaleOrder, self).write(vals)
        self._remove_unwanted_followers()
        return result
    

    @api.depends('message_follower_ids', 'user_id')
    def _compute_remove_unwanted_followers(self):
        """Compute method to remove unwanted followers"""
        print("hello word----------------------->its follower_restrict 44")
        for order in self:
            order.remove_follower = False  # Ensuring the field gets a value
            order._remove_unwanted_followers()

    def _remove_unwanted_followers(self):
        """Helper method to remove unwanted followers from Sale Order"""
        for order in self:
            print("hello word----------------------->its follower_restrict 5465")
            user_partner = order.user_id.partner_id.id if order.user_id else False
            unsubscribe_followers = [
                follower.partner_id.id
                for follower in order.message_follower_ids
                if follower.partner_id.id != user_partner
            ]
            if unsubscribe_followers:
                print("umfollower",unsubscribe_followers)
                order.message_unsubscribe(unsubscribe_followers)
