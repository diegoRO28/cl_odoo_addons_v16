# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MoodleActividadPlataforma(models.Model):
    """Avance de 'activity completion' en la Plataforma, por unidad y por
    estudiante.

    Es el equivalente, del lado de Moodle, a 'standard.actividades' (las
    actividades normales que el profesor califica manualmente en Odoo):
    una fila por estudiante y por actividad/unidad. La diferencia es que
    aquí no hay calificación manual — el total y lo realizado se traen
    tal cual los reporta la Plataforma vía 'activity completion'.
    """

    _name = 'moodle.actividad.plataforma'
    _description = 'Avance de Actividades (Activity Completion) en la Plataforma'
    _order = 'evaluacion_id, unidad_orden, student_id'

    evaluacion_id = fields.Many2one(
        'standard.evaluacion', string='Evaluación',
        required=True, ondelete='cascade',
    )
    student_id = fields.Many2one(
        'student.student', string='Estudiante',
        required=True, ondelete='cascade',
    )
    unidad_orden = fields.Integer(
        string='Orden', help="Posición de la unidad dentro del curso en la Plataforma.",
    )
    unidad_moodle_id = fields.Integer(
        string='ID de sección en Plataforma',
    )
    unidad_nombre = fields.Char(string='Unidad')

    total_actividades = fields.Integer(
        string='Actividades de la unidad',
        help="Cantidad de actividades de esta unidad que tienen activado "
             "el seguimiento de finalización ('activity completion') en la Plataforma.",
    )
    actividades_completadas = fields.Integer(
        string='Actividades completadas',
        help="Cantidad de esas actividades que el estudiante ya completó "
             "según la Plataforma.",
    )
    porcentaje_completado = fields.Float(
        string='% Completado', compute='_compute_porcentaje_completado', store=True,
    )

    @api.depends('total_actividades', 'actividades_completadas')
    def _compute_porcentaje_completado(self):
        for rec in self:
            rec.porcentaje_completado = (
                (rec.actividades_completadas / rec.total_actividades * 100.0)
                if rec.total_actividades else 0.0
            )
