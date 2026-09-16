# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SubjectSubjectMoodle(models.Model):
    """Agrega el código de curso en Moodle al catálogo de cursos de school."""

    _inherit = 'subject.subject'

    code_moodle = fields.Char(
        string='Código Moodle',
        help="Shortname del curso en Moodle. Debe coincidir exactamente "
             "con el 'Nombre corto del curso' configurado en Moodle.",
    )


class SchoolStandardMoodle(models.Model):
    """Cache del ID de curso en Moodle por sección."""

    _inherit = 'school.standard'

    moodle_course_id = fields.Integer(
        string='ID de curso en Moodle',
        help="Cache del ID de curso en Moodle, obtenido en la última "
             "sincronización de una inscripción de esta sección.",
    )
