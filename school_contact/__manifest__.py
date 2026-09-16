# -*- coding: utf-8 -*-
{
    'name': "Campos Contacs-class",
    'summary': """
        Campo contact - class""",
    'description': """
       Campos personalizados
    """,
    'author': "IT SOLUCIONES WEB",
    'website': "",
    'category': '',
    'version': '1.0',
    "depends": ["base", "sale_management", "stock", "account","school"],
    'data': [
       'security/ir.model.access.csv',
       
        'views/res_partner_form_inh.xml',
        'views/stock_scrap_form_inh.xml',
        

    ],
    'images': ['static/description/1010.png'],
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}