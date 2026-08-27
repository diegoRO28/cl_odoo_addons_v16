# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class SubjectAsistencia(models.Model):
    _inherit = "subject.asistencia"

    # Cambiando traducción del campo Selection:
    state        = fields.Selection([('draft', 'Preinscrito'), 
                              ('done', 'Inscrito'),
                              ('terminate', 'Culminado'), 
                              ('cancel', 'Retirado')], 
                              'Status', readonly=True, default="draft", help='State of the student registration form')