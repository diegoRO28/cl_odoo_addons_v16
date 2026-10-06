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
