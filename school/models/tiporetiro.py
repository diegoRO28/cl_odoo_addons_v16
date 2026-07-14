# See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

class SchoolTipoRetiro(models.Model):
    ''' Defining School Information'''

    _name = 'school.tiporetiro'
    _description = 'Tipo de Retiro'
    _order = "name asc"
    _check_company_auto = True

    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if self.env["school.tiporetiro"].search(
                [('code', '=', record.code), ('id', '!=', record.id)]):
                raise ValidationError("El código debe ser único")

    name = fields.Char('Nombre', store=True, help='Nombre del Tipo de Retiro')
    code = fields.Char('Código', required=True, help='Code')

    
