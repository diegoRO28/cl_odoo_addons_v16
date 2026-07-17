# custom_grade/models/registroeva_inherit.py
from odoo import api, fields, models

class StandardEvaluacionInherit(models.Model):
    _inherit = 'standard.evaluacion'
    
    def get_escala_custom(self):
        """Obtener escala personalizada para evaluaciones"""
        califica_vals = super().get_escala()
        
        if self.grade_id and self.grade_id.grade_ids:
            grade_line = self.grade_id.grade_ids[0]
            
            if hasattr(grade_line, 'honor_roll_threshold'):
                califica_vals['honor_roll'] = grade_line.honor_roll_threshold
                califica_vals['is_custom'] = grade_line.is_custom
        
        return califica_vals
    
    def asignar_state_evaluacion_custom(self, asigna):
        """Método extendido para asignar estados con lógica personalizada"""
        califica_vals = self.get_escala_custom()
        
        # Llamar al método original
        result = super().asignar_state_evaluacion(asigna)
        
        # Lógica para cuadro de honor
        if califica_vals.get('honor_roll'):
            for evaluacion in self.evaluacion_ids:
                if evaluacion.nota >= califica_vals['honor_roll']:
                    evaluacion.state = 'honor_roll'
        
        return result