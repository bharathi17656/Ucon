{
    'name': 'CRM Dashboard by AssistMates ',
    'version': '19.0.1.0.0',
    'author': 'bharathikannan17656@gmail.com',
    'depends': ['base', 'crm', 'web', 'sale', 'hr', 'payment_collection', 'mail'],     
    'data': [
        'security/dashboard_security.xml',
        'security/ir.model.access.csv',
        'views/crm_dashboard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crm_dashboard/static/src/crm_dashboard.js',
            'crm_dashboard/static/src/crm_dashboard.css',
            'crm_dashboard/static/src/crm_dashboard.xml',
        ],
    },
    'installable': True,
    'license': "LGPL-3",
}
