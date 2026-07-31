# -*- coding: utf-8 -*-
{
    'name': 'cl_retiros - Estado Flotante Reversible',
    'version': '16.0.1.0.0',
    'category': 'School',
    'summary': 'Extiende el módulo de retiros con un estado intermedio Flotante reversible',
    'description': """
        Agrega la funcionalidad de Estado Flotante al Registro de Retiros.
        El estudiante puede pasar de Inscrito a Flotante (congelando notas y cupos).
        De Flotante puede pasar a Retirado (baja definitiva) o Reactivarse a Inscrito (reversible).
        Todo sin crear nuevos menús ni modelos, solo extendiendo el módulo padre 'school'.
    """,
    'author': 'Tu Nombre',
    'website': 'https://www.tusitio.com',
    'depends': ['school'],  # Depende únicamente del módulo padre
    'data': [
        'security/ir.model.access.csv', # Opcional: para permisos
        'views/retiro_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}