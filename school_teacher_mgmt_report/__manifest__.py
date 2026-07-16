# -*- coding: utf-8 -*-
{
    'name': 'School Teacher Management Report',
    'summary': 'Reporte de Gestión Docente para el módulo School',
    'description': """
        Este módulo extiende el módulo School para añadir un reporte de
        "Gestión Docente". Se accede desde un nuevo menú "Reportes" bajo
        el menú "Gestión" en la barra de navegación principal.
        
        El reporte permite filtrar por Profesor, Curso o Código de Sección.
    """,
    'author': 'Tu Nombre',
    'category': 'Education',
    'version': '16.0.1.0.0',
    'website': 'https://www.tusitio.com',
    
    'depends': [
        'base',
        'school',
        'report_xlsx',
    ],
    
    'license': 'AGPL-3',
    
    'data': [
        'security/ir.model.access.csv',
        'views/teacher_mgmt_wizard_view.xml',
        'views/menu_extension.xml',
        'reports/report_teacher_mgmt_xlsx.xml',
    ],
    
    'images': [
        'static/description/icon.jpg'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}