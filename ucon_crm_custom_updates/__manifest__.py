{
    'name': 'Ucon CRM Leads Custom Changes  ',
    'version': '19.0.1.0.0',
    'author': 'bharathikannan17656@gmail.com',
    'depends': ['base','crm', 'web','sale_crm','sale','ucon_update_r1','ucon_crm_custom_updates_models'],
    'data': [
      
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'views/res_users_view.xml',
        
        
    ],
   
    'installable': True,
    'license': "LGPL-3",
}
