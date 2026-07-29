# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class StudentInscripcion(models.Model):

    _inherit = 'student.inscripcion'

    def action_set_draft(self):
        for rec in self:
            if rec.standard_id.state == 'done':
                raise UserError(_(f'No puede reestablecer a borrador la inscripción porque la sección {rec.standard_id.name} ya ha iniciado.'))
            rec.write({'state': 'draft'})