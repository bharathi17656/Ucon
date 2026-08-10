{
    "name": "Ucon Update R1",
    "version": "19.0.1.0.0",
    "summary": "Ucon Update for crm module .",
    "author": "bharathikannan17656@gmail.com",
    "depends": ['base', 'crm', 'web', 'sale', 'sale_crm', 'project', 'hr', 'mail'],
    "data": [
        'data/crm_stage_data.xml',
        'data/custom_assign_email.xml',
        'security/crm_lead_security.xml',
        'security/ir.model.access.csv',
        'views/crm_lead_view.xml',
        'views/employee_target.xml',
        'views/employee_target_view.xml',
    ],
    "assets": {
        "web.assets_backend": [
                
        ],    
    },
    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
