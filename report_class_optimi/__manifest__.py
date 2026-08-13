{
    'name': 'Report Class Optimized',
    'version': '16.0.1.0.0',
    'category': 'Education',
    'summary': 'Optimización de reportes académicos para secciones archivadas',
    'description': """
        Este módulo optimiza la generación de reportes académicos permitiendo
        visualizar las notas de estudiantes incluso cuando la sección está archivada.
        
        Características principales:
        - Visualización de notas en secciones archivadas
        - Mejora en la obtención de datos históricos
        - Compatibilidad con todos los reportes del módulo report_class
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': [
        'report_class',  # Dependencia del módulo padre
        'school',        # Módulo base de gestión académica
    ],
    'data': [
        'views/wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}