
from odoo import models


class PurchaseOrder(models.Model):
    """Inherits the purchase order for disable the follower"""
    _inherit = 'purchase.order'

    def button_confirm(self):
        """Check whether 'Disable Follower' is enabled.
            Check whether user and vendor are same.
            If not unsubscribe the vendor from followers list."""
        result = super(PurchaseOrder, self).button_confirm()
        if self.env['ir.config_parameter'].get_param(
                "follower_restrict.disable_followers"):
            user_partner = self.user_id.partner_id.id if self.user_id else False
            unsubscribe_followers = [follower.partner_id.id for follower in
                                     self.message_follower_ids if
                                     follower.partner_id.id != user_partner]
            if unsubscribe_followers:
                self.message_unsubscribe(unsubscribe_followers)
        return result
