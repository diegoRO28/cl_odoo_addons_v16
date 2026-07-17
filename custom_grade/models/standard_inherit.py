# custom_grade/models/standard_inherit.py
from odoo import api, fields, models

class SchoolStandardInherit(models.Model):
    _inherit = 'school.standard'
    
    def get_escala_custom(self):
        """Obtener la escala con configuración personalizada"""
        califica_vals = super().get_escala()
        
        if self.grade_id and self.grade_id.grade_ids:
            grade_line = self.grade_id.grade_ids[0]
            
            # Añadir información personalizada
            if hasattr(grade_line, 'honor_roll_threshold'):
                califica_vals['honor_roll'] = grade_line.honor_roll_threshold
                califica_vals['is_custom'] = grade_line.is_custom
                califica_vals['description'] = grade_line.description
            
            # Calcular porcentaje de aprobación
            if grade_line.base_mark > 0:
                califica_vals['pass_percentage'] = (grade_line.pass_mark / grade_line.base_mark) * 100
        
        return califica_vals