# See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

class SchoolPrograma(models.Model):
    ''' Defining School Information'''

    _name = 'school.programa'
    _description = 'Programa Information'
    _order = "name asc"

    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if self.env["school.programa"].search(
                [('code', '=', record.code), ('id', '!=', record.id)]):
                raise ValidationError("El código debe ser único")

    name      = fields.Char('Nombre', store=True, help='Nombre del Tipo de Evaluación')
    code      = fields.Char('Código', required=True, help='Code')
    is_active = fields.Boolean('¿ Activo?', default=True, help="Indica si activo")

    
