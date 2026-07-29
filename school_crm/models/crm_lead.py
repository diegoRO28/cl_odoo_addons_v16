# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class Lead(models.Model):
    _inherit = "crm.lead"
    
    student_id = fields.Many2one('student.student', string='Estudiante')
    is_company_partner = fields.Boolean('¿Es una organización/compañía?')
    is_won = fields.Boolean(related='stage_id.is_won')

    # Datos del estudiante (para que el usuario ingrese los datos):
    student_code = fields.Char('Código', help='Código del estudiante.', tracking=True)
    student_ci = fields.Char('Identificación', help='Número de cédula.', tracking=True)
    school_id = fields.Many2one('school.campus', 'Sede', tracking=True)
    gender = fields.Selection([('masculino', 'Masculino'), ('femenino', 'Femenino')], string='Sexo')
    school_parent_ids = fields.Many2many('school.parent', 'opportunity_school_parent_rel',
        'opportunity_id', 'school_parent_id', 'Representante(s)',
        help='Ingrese el o los representantes del estudiante')

    # Datos del estudiante (relacionados):
    student_code_related = fields.Char(related='student_id.student_code')
    student_ci_related = fields.Char(related='student_id.student_ci')
    school_id_related = fields.Many2one(related='student_id.school_id')
    gender_related = fields.Selection(related='student_id.gender')
    school_parent_ids_related = fields.Many2many('school.parent', 'opportunity_school_parent_related_rel',
        'opportunity_id', 'school_parent_id', 'Representante(s)', compute='_compute_school_parent_ids_related')

    @api.depends('student_id', 'student_id.parent_id')
    def _compute_school_parent_ids_related(self):
        for rec in self:
            rec.school_parent_ids_related = False
            if rec.student_id:
                if rec.student_id.parent_id:
                    rec.school_parent_ids_related = [(6, 0, rec.student_id.parent_id.ids)]

    # @api.onchange('partner_id')
    # def _onchange_partner_id(self):
    #     for rec in self:
    #         if rec.partner_id:
    #             if rec.partner_id.is_company:
    #                 rec.is_company_partner = True
    #             else:
    #                 rec.is_company_partner = False

    def action_create_student(self):
        for rec in self:
            if not rec.student_code:
                raise ValidationError(_('Por favor, ingrese el código del estudiante.'))
            if not rec.school_id:
                raise ValidationError(_('Por favor, ingrese la sede del estudiante.'))
            if not rec.student_ci:
                raise ValidationError(_('Por favor, ingrese la identificación del estudiante.'))                                
            if not rec.gender:
                raise ValidationError(_('Por favor, ingrese el sexo/género del estudiante.'))                                            

            # Creando el estudiante:
            student_id = self.env['student.student'].with_context(default_type=False).create({
                'name': rec.partner_id.name,
                'student_code': rec.student_code,
                'student_ci': rec.student_ci,
                'school_id': rec.school_id.id,
                'gender': rec.gender,
                # Representante(s):
                'parent_id': [(6, 0, rec.school_parent_ids.ids)] if rec.school_parent_ids else False,                
                # Asociar CRM:
                'opportunity_id': rec.id, 
            })

            # Asignando el estudiante al registro de CRM:
            rec.student_id = student_id.id