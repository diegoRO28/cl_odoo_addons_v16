# See LICENSE file for full copyright and licensing details.
{
    'name': 'Plataforma',
    'version': '16.0.1.0.0',
    'category': 'Gestion Academica de Centros de Estudios',
    'summary': 'Integración de Class (school) con Moodle vía Web Services REST',
    'description': """
Plataforma - Integración Class <-> Moodle (TEG)
=================================================
Alcance de esta versión (Fase 0/1 del plan de arquitectura completo):
    * Al confirmar una inscripción (student.inscripcion -> admission_done):
      busca o crea el usuario del estudiante en Moodle y lo matricula en el
      curso correspondiente (por 'Código Moodle').
    * Pantalla de configuración de conexión (URL, token, timeout, etc.).
    * Log de auditoría de cada llamada a la API de Moodle.

El resto del alcance (Retiros, Cambios, Estudiantes, Secciones,
Evaluaciones, dashboards de Gestión, reactivación por pago) está
documentado en el plan de arquitectura y se irá agregando en fases
posteriores sobre esta misma base.

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
        'views/inscripcion_views.xml',
    ],
    'installable': True,
    'application': False,
}
