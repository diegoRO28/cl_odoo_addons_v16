# custom_grade/models/grade_line.py
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class GradeLineInherit(models.Model):
    _inherit = 'grade.line'
    
    # Redefinir pass_mark como Float para permitir decimales
    pass_mark = fields.Float(
        string='Calificación de Aprobación',
        required=True,
        digits=(3, 1),  # 3 dígitos totales, 1 decimal (ej: 17.5)
        help='Nota mínima para aprobar (configurable por institución)'
    )
    
    # Añadir nuevos campos (también como Float)
    honor_roll_threshold = fields.Float(
        string='Cuadro de Honor',
        help='Nota mínima para cuadro de honor',
        digits=(3, 1),
        default=19.0
    )
    
    is_custom = fields.Boolean(
        string='Escala Personalizada',
        default=False,
        help='Indica si esta es una escala personalizada'
    )
    
    description = fields.Text(
        string='Descripción de la Escala',
        help='Descripción personalizada de la escala'
    )
    
    # Validación personalizada
    @api.constrains('pass_mark')
    def _check_custom_pass_mark(self):
        for record in self:
            if record.pass_mark < 10.0:
                raise ValidationError("La calificación de aprobación no puede ser menor a 10")
            if record.pass_mark > record.base_mark:
                raise ValidationError("La calificación de aprobación no puede ser mayor a la Escala Base")
    
    # Método para obtener información extendida de la escala
    def get_grade_info(self):
        """Obtener información completa de la escala con configuración personalizada"""
        return {
            'base': self.base_mark,
            'min': self.from_mark,
            'max': self.to_mark,
            'pass': self.pass_mark,
            'honor_roll': self.honor_roll_threshold,
            'is_custom': self.is_custom,
            'description': self.description,
        }