# Copyright 2025 AssistMates
# Author: Bharathikannan M <bharathikannan17656@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html)
# 
# This module allows users to forward messages from the chatter of any document 
# to other users via email, improving communication and workflow efficiency 
# within Odoo.
{
    "name": "Mail Forward Message",
    "version": "19.0.1.0.0",
    "summary": "Forward messages from the chatter of any document to other users.",
    "author": "Bharathikannan.M",
    'maintainer': 'bharathikannan17656@gmail.com',
    "depends": ["mail", "contacts"],
    'category': 'Marketing/Email Marketing',
    "data": [
      
    ],
    "assets": {
        "web.assets_backend": [
            "mail_forward/static/src/components/forward_message.js",
            
        ],
        
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
