
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Inherits the config settings for adding disable option"""
    _inherit = 'res.config.settings'

    disable_followers = fields.Boolean(
        "Disable Followers",
        config_parameter="follower_restrict.disable_followers",
        help="Enable the follower restrict", default=True)
