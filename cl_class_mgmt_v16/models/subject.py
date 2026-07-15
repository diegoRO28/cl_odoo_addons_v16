# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SubjectEncuentros(models.Model):
    _inherit = 'subject.encuentros'

    es_evaluacion = fields.Boolean(
        string='Es Evaluación',
        help='Marca este encuentro como una evaluación. La posición de '
             'este encuentro dentro del plan (campo Secuencia) es la que '
             'usa el sistema para calcular la fecha correcta de las '
             'evaluaciones en las secciones del curso.')
