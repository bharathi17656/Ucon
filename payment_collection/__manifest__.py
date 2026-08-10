{
    "name": "Payments Collection for Employees",
    "version": "19.0.1.0.0",
    "author": "Bharathikannan.M",
    "maintainer": "bharathikannan17656@gmail.com",
    "depends": ["mail", "crm","sale","sale_crm","hr"],
   'data': [
       
    'security/employee_payment_security.xml',
    'security/ir.model.access.csv',
    'data/bulk_mail_remainder.xml',
    'views/employee_payment_collection_views.xml',
    ],
    'assets': {
    'web.assets_backend': [
        # 'payment_collection/static/src/soa_upload_popup.js',
        # 'payment_collection/static/src/soa_upload_popup.xml',
    ],
},


    "installable": True,
    "auto_install": False,
    "license": "AGPL-3",
}
