# See LICENSE file for full copyright and licensing details.
{
    'name': 'Plataforma',
    'version': '16.0.1.0.0',
    'category': 'Gestion Academica de Centros de Estudios',
    'summary': 'Integración de Class (school) con Moodle vía Web Services REST',
    'description': """
Plataforma - Integración Class <-> Moodle (TEG)
=================================================
Alcance de esta versión:
    * Inscripciones: crea/actualiza el usuario del estudiante en Moodle,
      lo matricula en el curso ('Código Moodle') y lo agrega al grupo de
      su sección, con cálculo de vencimiento desde Odoo.
    * Retiros: suspende la matrícula del estudiante en el curso (no su
      cuenta ni su acceso a otros cursos).
    * Cambios de sección: mueve al estudiante del grupo de la sección
      origen al de la sección destino.
    * Estudiantes: alta/actualización reactiva de la cuenta y verificación
      en vivo del estado y los cursos matriculados.
    * Secciones: sincronización diferencial por lotes del grupo y sus
      integrantes, con caché de IDs y métricas en la interfaz.
    * Evaluaciones: relaciona cada evaluación del libro con su(s)
      unidad(es) en Moodle (agrupación automática cuando la cantidad de
      unidades es múltiplo de la de evaluaciones) y trae, por estudiante,
      el avance de 'activity completion' de esa unidad.
    * Pantalla de configuración de conexión (URL, token, timeout, etc.)
      y log de auditoría de cada llamada a la API de Moodle, segmentado
      por Administración, Estudiante, Secciones y Evaluaciones.

Fuera del alcance de esta versión (documentado como trabajo futuro, no
incluido en esta entrega): sincronización de Docentes, reactivación
automática de matrículas por pago, y una tarea programada de supervisión
periódica.

Arquitectura (conector activo por herencia):
    * No modifica el módulo "school" directamente.
    * Toda la integración vive en este módulo vía _inherit.
    * Reversible: al desinstalarlo, "school" queda intacto.
    * El menú "Plataforma" vive DENTRO del menú de Class (no es una app
      aparte en el selector de apps de Odoo).
""",
    'author': 'Diego - TEG',
    'license': 'AGPL-3',
    'depends': ['school'],
    'data': [
        'security/ir.model.access.csv',
        'views/moodle_config_views.xml',
        'views/sync_log_views.xml',
        'views/sync_log_menus.xml',
        'views/inscripcion_views.xml',
        'views/retiro_views.xml',
        'views/cambio_views.xml',
        'views/student_views.xml',
        'views/standard_views.xml',
        'views/subject_views.xml',
        'views/evaluacion_views.xml',
        'views/bulk_actions_views.xml',
    ],
    'installable': True,
    'application': False,
}
