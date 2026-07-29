{
    'name': 'OdooClass Optimize',
    'version' : '1.0',
    'description': """
        Enhances and simplifies views in your school management system, 
        ensuring a smoother user experience and improved efficiency 
        for administrators, teachers, and students.
    """,    
    'summary': 'OdooClass Optimize',
    'depends': ['school_contact'],
    'data': [
        # Security:
        'security/res_users_security.xml',
        'security/account_security.xml',
        'security/ir.model.access.csv',

        # Views:
        'views/sale_order_views.xml',
        'views/parent_view.xml',
        'views/student_view.xml',
        'views/inscripcion_view.xml',
        'views/libroeva_view.xml',
        'views/account_move_views.xml',
        'views/account_journal_views.xml',
        'views/account_payment_views.xml',
        'views/account_payment_concept_views.xml',
        'views/account_custom_payment_terms_views.xml',

        # Wizard:
        'wizard/account_payment_register_views.xml',        
    ],
    'post_init_hook': '_school_post_init',
}