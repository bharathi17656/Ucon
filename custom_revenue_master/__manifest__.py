# Copyright 2025 AssistMates
# Author: Bharathikannan M <bharathikannan17656@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0.html)

{
    "name": "Custom Revenue Master",
    "version": "19.0.1.0.0",
    "summary": "Create monthlywise Revenue model for Client requirement.",
    "author": "Bharathikannan.M",
    "maintainer": "bharathikannan17656@gmail.com",
    "depends": ["sale", "crm", "hr", "account", "mail"],

    "data": [
      
        "security/ir.model.access.csv",
          "views/revenue_master.xml",
    ],

    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
