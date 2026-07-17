# report_class/models/grade_mixin.py
# -*- coding: utf-8 -*-

from odoo import models, api


class GradeMixin(models.AbstractModel):
    """Mixin para obtener la escala con soporte para custom_grade"""
    _name = 'grade.mixin'
    _description = 'Mixin para obtener escala de calificaciones'

    @api.model
    def get_escala_custom(self, standard_id=None):
        """
        Obtiene la escala con soporte para custom_grade.
        
        Args:
            standard_id (recordset, optional): Registro de school.standard para obtener su escala específica.
            
        Returns:
            dict: Diccionario con los valores de la escala.
        """
        califica_vals = {
            'minimo': 0,
            'maximo': 0,
            'aprobado': 0,
            'base': 0
        }
        
        # Intentar obtener desde grade.line
        escalaObj = self.env['grade.line'].sudo().search([('sequence', '=', '1')], limit=1)
        
        if escalaObj:
            califica_vals = {
                'minimo': escalaObj.from_mark,
                'maximo': escalaObj.to_mark,
                'aprobado': escalaObj.pass_mark,
                'base': escalaObj.base_mark
            }
            
            # Verificar si custom_grade está instalado
            custom_grade_installed = self.env['ir.module.module'].sudo().search([
                ('name', '=', 'custom_grade'),
                ('state', '=', 'installed')
            ])
            
            if custom_grade_installed:
                try:
                    if standard_id:
                        # Obtener la escala de la sección específica
                        if hasattr(standard_id, 'grade_id') and standard_id.grade_id:
                            grade_line = standard_id.grade_id.grade_ids[0]
                            califica_vals['aprobado'] = grade_line.pass_mark
                            califica_vals['base'] = grade_line.base_mark
                    else:
                        # Buscar la primera escala no cancelada
                        scale = self.env['grade.master'].search(
                            [('state', '!=', 'cancel')],
                            limit=1
                        )
                        if scale and scale.grade_ids:
                            grade_line = scale.grade_ids[0]
                            califica_vals['aprobado'] = grade_line.pass_mark
                except Exception:
                    # Si algo falla, mantener el valor original
                    pass
        
        return califica_vals