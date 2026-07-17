{
    'name': 'Custom Grade System',
    'version': '1.0',
    'category': 'Education',
    'summary': 'Sistema personalizado de escalas de calificación',
    'description': """
        Módulo hijo que extiende la funcionalidad de escalas de calificación
        permitiendo configuración personalizada sin modificar el módulo padre.
    """,
    'author': 'Tu Empresa',
    'depends': ['school'],
    'data': [
        'security/ir.model.access.csv',
        'views/grade_line_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}