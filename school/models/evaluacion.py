# See LICENSE file for full copyright and licensing details.

# import time
import calendar
import re

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.translate import _
#-----------------------------------------------------------------------#
# DESARROLLO PROPIO: SE AGREGO ESTA CLASE                               #
#-----------------------------------------------------------------------# 
    
class SubjectEvaluacion(models.Model):
    _name = "subject.evaluacion"
    _description = "(MAESTRO) Registro de Evaluaciones / Curso "
    _inherit = ['mail.thread', 'mail.activity.mixin']

    #-----------------------------------------------------------------------#
    @api.depends('state')
    def _compute_state(self):
        '''Method to compute total student.'''
        for rec in self:
            rec.state_aux = self.get_estado(rec.state)
    #-----------------------------------------------------------------------#

    name = fields.Char(string='RE Nro.', required=True, copy=False, readonly=True, default=lambda self: _('New'))

    standard_id   = fields.Many2one('school.standard', 'Sección', required=True, help='Standard')
    subject_id    = fields.Many2one('subject.subject', 'Curso', required=True, help='Curso')
    evaluacion_id = fields.Many2one('subject.planevaluacion', 'Evaluación', required=True, help='Evaluación')
    teacher_id    = fields.Many2one('school.teacher', 'Profesor', required=True, help='Profesor')

    #name = fields.Char(string='Nombre', store=True, required=True)
    #code = fields.Char('Código', required=True, help='Código/Secuencia del encuentro')
    note = fields.Text('Observaciones', help='Observaciones')
    peso = fields.Integer('Peso', default=0, help='Escriba el peso de la evaluación')
    date_start = fields.Date('Fecha de inicio', required=True, help='Starting date of Lapso Académico', default=fields.Date.today)
    average_o    = fields.Float('Evaluaciòn Oral', help='Escriba la evaluación Oral', default=0)
    average_e    = fields.Float('Evaluaciòn Escrita', help='Escriba la evaluación Oral', default=0)
    average_t    = fields.Float('Total', help='Escriba la evaluación Oral', default=0)

    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'),
        ('terminate', 'Terminate'), ('cancel', 'Cancel')], 'Status', readonly=True, default="draft",
        tracking=True, help='State of the student registration form')
    
    state_aux        = fields.Selection([('por iniciar', 'Por iniciar'), 
                                         ('iniciado', 'Iniciado'),
                                         ('culminado', 'Culminado'), 
                                        ], 'Registro Inscripciòn', readonly=True, default="por iniciar", tracking=True, help='State of the student registration form'
                                        , compute="_compute_state")

    
    evaluacion_ids = fields.One2many('subject.evaluaciones', 'evaluacion_id', string="Registro de Evaluaciones")

#-----------------------------------------------------------------------#
    @api.model
    def create(self, vals):
          if vals.get('name', _('New')) == _('New'):
              vals['name'] = self.env['ir.sequence'].next_by_code('evaluacion.code') or _('New')
          res = super(SubjectEvaluacion, self).create(vals)
          return res
#-----------------------------------------------------------------------#    
    def set_draft(self):
        '''Method to change state to draft'''
        self.state = 'draft'
#-----------------------------------------------------------------------#
    def set_done(self):
        '''Method to change state to done'''
       
        no_students = self.get_no_students()
        if no_students!=0:
            self.state = 'done'
            self.generate_record_evaluacion(no_students)
        else:
            raise ValidationError(_( "Error : No hay estudiantes en el curso" ))
#-----------------------------------------------------------------------#
    def set_terminate(self):
        '''Set the state to terminate'''
        self.asignar_state_evaluacion()
        self.state = 'terminate'
#-----------------------------------------------------------------------#
    def set_cancel(self):
        '''Set the state to cancel.'''
        self.state = 'cancel'

#-----------------------------------------------------------------------#
    def set_done_corregir(self):
        '''Method to change state to done - confirm'''
       
        if self.standard_id.state != 'terminate':
            self.asignar_state_corregir()
            self.state = 'done'
        else:
            raise ValidationError(_( "Error : No se puede VOLVER A INICIADO porque la SECCIÒN està CERRADA" ))    

#-----------------------------------------------------------------------#
    def get_estado(self , sta):
        '''Method to compute la escala minima.'''

        if sta == 'draft':
           return 'por iniciar'
        elif sta == 'done':
           return 'iniciado' 
        elif sta == 'terminate':
           return 'culminado'
        
        else:
            return sta
        
        return sta    
#-----------------------------------------------------------------------#
    def get_no_students(self):
        '''Method to compute subjects.'''
        contador = 0
        for rec in self:
             #nombre = rec.standard_id.student_ids[0].student_code
             contador = len(rec.standard_id.student_ids)

        return contador
#-----------------------------------------------------------------------#    
    def get_escala(self):
        '''Method to compute la escala minima.'''

        califica_vals = {'minimo': 0, 'maximo': 0 , 'aprobado': 0 }
  
        escalaObj = self.env['grade.line'].sudo().search([('sequence', '=', '1')], limit=1)

        if escalaObj:
           califica_vals = {'minimo': escalaObj.from_mark, 
                            'maximo': escalaObj.to_mark,
                            'aprobado': escalaObj.pass_mark
                           }
        
        return califica_vals
#-----------------------------------------------------------------------#
    def generate_record_evaluacion(self, no_students):
        """Generate registro de Evaluacion por seccion / Curso."""

        i = 1

        evaluacion_obj = self.env['subject.evaluaciones']

        for rec in self:
            if no_students!=0:
               while i <= no_students:
                   
                   stu_ri = rec.standard_id.student_ids[i-1].id
                   stu_id = rec.standard_id.student_ids[i-1].student_id.id
                   stu_state = rec.standard_id.student_ids[i-1].state
                   #-----------------------------------------------------------------------#
                   # GENERA EL REGISTRO A LOS STUDENT DONE                                  #
                   #-----------------------------------------------------------------------#

                   if stu_state == 'done':
                        evaluacion_obj.create({
                            'inscripcion_id': stu_ri,
                            'evaluacion_id' : rec.id,
                            'student_id'    : stu_id,

                            'eva_oral': 0,
                            'eva_esc': 0,
                            'rec_oral': 0,
                            'rec_esc': 0,
                            'is_recupera': False,
                            'eva_total': 0,
                            'note': " ",
                            
                        })
                   #raise ValidationError("GENERANDO LAS EVALUACIONES: ..!" + "STU_ID:" + str(stu_id) + "EVA_ID:" + str(rec.id))

                   i = i + 1

#-----------------------------------------------------------------------#   
    def asignar_califica_oral(self, registro):
        '''Method to calculate calificacion total'''

        calificaVals = self.get_escala()
        
        for reg in registro:
          
            if reg.is_recupera:
                if reg.rec_oral != 0:
                     return reg.rec_oral
                else:
                     return reg.eva_oral

#-----------------------------------------------------------------------#   
    def asignar_califica_escrita(self, registro):
        '''Method to calculate calificacion total'''

        calificaVals = self.get_escala()
        
        for reg in registro:
          
            if reg.is_recupera:
                if reg.rec_esc != 0:
                     return reg.rec_esc
                else:
                     return reg.eva_esc

#-----------------------------------------------------------------------#
    def asignar_state_evaluacion(self):
        """Generate registro de Evaluacion por seccion / Curso."""
        acum_o = 0
        acum_e = 0
        acum_t = 0
        conta  = 0

        calificaVals = self.get_escala()
        evaluaciones = self.env['subject.evaluaciones'].search([('evaluacion_id', '=', self.id)])
        
        for registro in evaluaciones:

            conta+= 1
            acum_o+=registro.eva_oral
            acum_e+=registro.eva_esc
            acum_t+=registro.eva_total

            evalua = 0

            if registro.is_recupera:
                if self.asignar_califica_oral(registro) >= calificaVals['aprobado'] and self.asignar_califica_escrita(registro) >= calificaVals['aprobado']:
                    registro.state = 'aprobado'
                else:
                    registro.state = 'aplazado'

            else:

                if registro.eva_oral >= calificaVals['aprobado'] and registro.eva_esc >= calificaVals['aprobado']:
                    registro.state = 'aprobado'
                else:
                    registro.state = 'aplazado'
            

        if conta != 0:
            self.average_o = acum_o / conta
            self.average_e = acum_e / conta
            self.average_t = acum_t / conta

#-----------------------------------------------------------------------#
    def asignar_state_corregir(self):
        """Generate registro de Evaluacion para correccion"""
 
        
        evaluaciones = self.env['subject.evaluaciones'].search([('evaluacion_id', '=', self.id)])
        
        for rec in evaluaciones:
           
            rec.state = 'borrador'

            self.average_o = 0
            self.average_e = 0
            self.average_t = 0
    
 #-----------------------------------------------------------------------#
 # DESARROLLO PROPIO: SE AGREGO ESTA CLASE                               #
 #-----------------------------------------------------------------------# 
    
class SubjectEvaluaciones(models.Model):
    _name = "subject.evaluaciones"
    _description = "(DETALLE) Registro / Evaluaciones / Estudiantes"
    _order = "student_id asc"
#-----------------------------------------------------------------------#    
    def get_escala(self):
        '''Method to compute la escala minima.'''

        califica_vals = {'minimo': 0, 'maximo': 0 , 'aprobado': 0 }
  
        escalaObj = self.env['grade.line'].sudo().search([('sequence', '=', '1')], limit=1)

        if escalaObj:
           califica_vals = {'minimo': escalaObj.from_mark, 
                            'maximo': escalaObj.to_mark,
                            'aprobado': escalaObj.pass_mark
                           }
        
        return califica_vals
    
#-----------------------------------------------------------------------#    
    # @api.depends('is_recupera')
    # def _compute_recupera(self):
    #     '''Method to compute total student.'''
    #     for reg in self:
    #         if reg.is_recupera:
    #              reg.rec_oral = 0
    #              reg.rec_esc  = 0

#-----------------------------------------------------------------------#   
    @api.depends('eva_oral','eva_esc','rec_oral','rec_esc')
    def _compute_total_eva(self):
        '''Method to calculate calificacion total'''

        calificaVals = self.get_escala()
        
        for rec in self:
          
            rec.eva_total = rec.eva_total

            if not rec.is_recupera:
                if (rec.eva_oral >= calificaVals['minimo']):
                    if (rec.eva_oral <= calificaVals['maximo']):
                        auxTot = (rec.eva_oral + rec.eva_esc)/2
                        rec.eva_total = auxTot
                    else:
                        rec.eva_oral = calificaVals['minimo']
                        raise ValidationError(_( "Error : La calificaciòn debe ser menor o igual a " + str(calificaVals['maximo']) ))
                else:
                        rec.eva_oral = calificaVals['minimo']
                        raise ValidationError(_( "Error : La calificaciòn debe ser mayor o igual a " + str(calificaVals['minimo']) ))
            
        for rec in self:
           
            rec.eva_total = rec.eva_total

            if not rec.is_recupera:
                if (rec.eva_esc >= calificaVals['minimo']):
                    if (rec.eva_esc <= calificaVals['maximo']):
                        auxTot = (rec.eva_oral + rec.eva_esc)/2
                        rec.eva_total = auxTot
                    else:
                        rec.eva_esc = calificaVals['minimo']
                        raise ValidationError(_( "Error : La calificaciòn debe ser menor o igual a " + str(calificaVals['maximo']) ))
                else:
                    rec.eva_esc = calificaVals['minimo']
                    raise ValidationError(_( "Error : La calificaciòn debe ser mayor o igual a " + str(calificaVals['minimo']) ))

        for rec in self:
            auxTot = 0

            if rec.is_recupera and rec.rec_oral > 0:
                if (rec.rec_oral >= calificaVals['minimo']):
                    if (rec.rec_oral <= calificaVals['maximo']):
                            if rec.rec_esc > 0:
                                auxTot = (rec.rec_oral + rec.rec_esc)/2
                            else:
                                auxTot = (rec.rec_oral + rec.eva_esc)/2
                            rec.eva_total = auxTot
                    else:
                        rec.rec_oral = calificaVals['minimo']
                        raise ValidationError(_( "Error : La calificaciòn debe ser menor o igual a " + str(calificaVals['maximo']) ))
                else:
                    rec.rec_oral = calificaVals['minimo']
                    raise ValidationError(_( "Error : La calificaciòn debe ser mayor o igual a " + str(calificaVals['minimo']) ))
        
        for rec in self:
            auxTot = 0

            if rec.is_recupera and rec.rec_esc > 0:
                if (rec.rec_esc >= calificaVals['minimo']):
                    if (rec.rec_esc <= calificaVals['maximo']):
                            if rec.rec_oral > 0:
                                auxTot = (rec.rec_oral + rec.rec_esc)/2
                            else:
                                auxTot = (rec.eva_oral + rec.rec_esc)/2
                            rec.eva_total = auxTot
                    else:
                        rec.rec_esc = calificaVals['minimo']
                        raise ValidationError(_( "Error : La calificaciòn debe ser menor o igual a " + str(calificaVals['maximo']) ))
                else:
                    rec.rec_esc = calificaVals['minimo']
                    raise ValidationError(_( "Error : La calificaciòn debe ser mayor o igual a " + str(calificaVals['minimo']) ))

                
#-----------------------------------------------------------------------#   
    @api.onchange('is_recupera')
    def onchange_is_recupera(self):

        for reg in self:
            
            reg.rec_oral = 0
            reg.rec_esc  = 0

#-----------------------------------------------------------------------#   
    @api.onchange('rec_oral','rec_esc')
    def onchange_recupera(self):

        '''Method to calculate calificacion total'''

        # calificaVals = self.get_escala()

        #-----------------------------------------------------------------------#
        #    RECUPERACIÒN (CALCULO DEL TOTAL)                                   #
        #-----------------------------------------------------------------------#    

        # for rec in self:
        #     auxTot = 0

        #     if rec.is_recupera and rec.rec_oral > 0:
        #         if (rec.rec_oral >= calificaVals['minimo']):
        #             if (rec.rec_oral <= calificaVals['maximo']):
        #                     if rec.rec_esc > 0:
        #                         auxTot = (rec.rec_oral + rec.rec_esc)/2
        #                     else:
        #                         auxTot = (rec.rec_oral + rec.eva_esc)/2
        #                     rec.eva_total = auxTot
        #             else:
        #                 rec.rec_oral = calificaVals['minimo']
        #                 raise ValidationError(_( "Error : La calificaciòn debe ser menor o igual a " + str(calificaVals['maximo']) ))
        #         else:
        #             rec.rec_oral = calificaVals['minimo']
        #             raise ValidationError(_( "Error : La calificaciòn debe ser mayor o igual a " + str(calificaVals['minimo']) ))
                
        # for rec in self:
        #     auxTot = 0

        #     if rec.is_recupera and rec.rec_esc > 0:
        #         if (rec.rec_esc >= calificaVals['minimo']):
        #             if (rec.rec_esc <= calificaVals['maximo']):
        #                     if rec.rec_oral > 0:
        #                         auxTot = (rec.rec_oral + rec.rec_esc)/2
        #                     else:
        #                         auxTot = (rec.eva_oral + rec.rec_esc)/2
        #                     rec.eva_total = auxTot
        #             else:
        #                 rec.rec_esc = calificaVals['minimo']
        #                 raise ValidationError(_( "Error : La calificaciòn debe ser menor o igual a " + str(calificaVals['maximo']) ))
        #         else:
        #             rec.rec_esc = calificaVals['minimo']
        #             raise ValidationError(_( "Error : La calificaciòn debe ser mayor o igual a " + str(calificaVals['minimo']) ))

#-----------------------------------------------------------------------#

    
    inscripcion_id = fields.Many2one('student.inscripcion', string='Registro Inscripciòn', required=True, help='Registro Inscripcion')
    evaluacion_id  = fields.Many2one('subject.evaluacion',  string="Evaluaciones", required=True)
    student_id     = fields.Many2one('student.student',     string='Estudiante', required=True, help='Estudiante')
    teacher_id    = fields.Many2one('school.teacher', 'Profesor', help='Profesor')

    eva_oral    = fields.Float('Evaluación Oral', help='Escriba la evaluación Oral', default=0)
    eva_esc     = fields.Float('Evaluación Escrita', help='Escriba la evaluación Escrita', default=0)
    is_recupera = fields.Boolean('Recuperaciòn?', default=False, help='Indica si la evaluaciòn es recuperaciòn is practical.')
    rec_oral    = fields.Float('Recuperaciòn Oral', help='Escriba la recuperaciòn Oral', default=0)
    rec_esc     = fields.Float('Recuperaciòn Escrita', help='Escriba la recuperacion Escrita', default=0)

    eva_total   = fields.Float('Promedio', readonly=True, help='Evaluación Promedio', default=0, compute='_compute_total_eva')
    note        = fields.Text('Observaciones', help='Observación')
    state       = fields.Selection([('borrador', 'Borrador'), 
                                    ('aprobado', 'Aprobado'),
                                    ('aplazado', 'Aplazado'), 
                                    ('inasistente', 'Inasistente'),
                                     ], 'Calificaciòn', readonly=True, default="borrador", help='State of the student registration form')

#-----------------------------------------------------------------------#