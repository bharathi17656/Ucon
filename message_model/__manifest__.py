{
    "name": "Message Notification Icon",
    "version": "19.0.1.0.0",
    "author": "Bharathikannan.M",
    "maintainer": "bharathikannan17656@gmail.com",
    "depends": ["mail", "crm","sale","sale_crm"],
    "data": [
        # "views/crm_lead_kanban_view.xml",
    ],
     'assets': {
        'web.assets_backend': [
           
            'message_model/static/src/message_notifi.css',
         
        ],
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
