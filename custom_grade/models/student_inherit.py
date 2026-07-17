# custom_grade/models/student_inherit.py
from odoo import api, fields, models

class StudentInscripcionInherit(models.Model):
    _inherit = 'student.inscripcion'
    
    # Añadir nuevo campo
    honor_roll = fields.Boolean(
        string='Cuadro de Honor',
        compute='_compute_honor_roll',
        store=True,
        help='Indica si el estudiante está en cuadro de honor'
    )
    
    @api.depends('nota', 'standard_id')
    def _compute_honor_roll(self):
        """Calcular si el estudiante está en cuadro de honor"""
        for record in self:
            record.honor_roll = False
            if record.standard_id:
                escala = record.standard_id.get_escala_custom()
                if escala.get('honor_roll') and record.nota >= escala['honor_roll']:
                    record.honor_roll = True
    
    def get_grade_status_custom(self):
        """Obtener estado de calificación con configuración personalizada"""
        if not self.standard_id:
            return 'sin_evaluacion'
        
        escala = self.standard_id.get_escala_custom()
        
        if self.nota >= escala.get('honor_roll', 19):
            return 'honor_roll'
        elif self.nota >= escala['aprobado']:
            return 'aprobado'
        else:
            return 'aplazado'