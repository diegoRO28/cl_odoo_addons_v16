{
    'name': 'OdooClass Integration with CRM',
    'version' : '1.0',
    'description': """
        OdooClass Integration with CRM
    """,    
    'summary': 'OdooClass Integration with CRM',
    'depends': [
        'crm',
        'school'
    ],
    'data': [
        # Security:
        'security/security.xml',

        # Views:
        'views/crm_lead_views.xml',
        'views/student_view.xml',
    ],
}