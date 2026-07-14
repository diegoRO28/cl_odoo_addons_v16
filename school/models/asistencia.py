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
    
class SubjectAsistencia(models.Model):
    _name = "subject.asistencia"
    _description = "(MAESTRO) Registro de Asistencia / Curso / Encuentros"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    #-----------------------------------------------------------------------#
    @api.depends('state')
    def _compute_state(self):
        '''Method to compute total student.'''
        for rec in self:
            rec.state_aux = self.get_estado(rec.state)
    #-----------------------------------------------------------------------#

    name         = fields.Char(string='RA Nro.', required=True, copy=False, readonly=True, default=lambda self: _('New'))

    standard_id  = fields.Many2one('school.standard', 'Sección', required=True, help='Standard')
    subject_id   = fields.Many2one('subject.subject', 'Curso', required=True, help='Curso')
    encuentro_id = fields.Many2one('subject.encuentros', 'Encuentro', required=True, help='Encuentros')
    teacher_id   = fields.Many2one('school.teacher', 'Profesor', required=True, help='Profesor')
    school_id    = fields.Many2one('school.campus', 'Campus', help='Campus', store=True)
    
    note         = fields.Text('Descripción', help='Descripción')
    date_start   = fields.Date('Fecha de inicio', required=True, help='Starting date of Lapso Académico', default=fields.Date.today)
    color        = fields.Integer('Color Index', help='Index of color')

    company_id   = fields.Many2one('res.company', 'Companía', related='standard_id.company_id', store=True, help='Company_id of the school')

    state        = fields.Selection([('draft', 'Draft'), 
                              ('done', 'Done'),
                              ('terminate', 'Terminate'), 
                              ('cancel', 'Cancel')], 
                              'Status', readonly=True, default="draft", help='State of the student registration form')
    
    state_aux    = fields.Selection([('por iniciar', 'Por iniciar'), 
                                         ('iniciado', 'Iniciado'),
                                         ('culminado', 'Culminado'), 
                                        ], 'Registro Inscripciòn', readonly=True, default="por iniciar", help='State of the student registration form'
                                        , compute="_compute_state")
    
    asistencia_ids = fields.One2many('subject.asistencias', 'asistencia_id', string="Registro de Asistencias")
#-----------------------------------------------------------------------#
    @api.model
    def create(self, vals):
          if vals.get('name', _('New')) == _('New'):
              vals['name'] = self.env['ir.sequence'].next_by_code('asistencia.code') or _('New')
          res = super(SubjectAsistencia, self).create(vals)
          return res    
#-----------------------------------------------------------------------#
    def set_draft(self):
        '''Method to change state to draft'''
        self.state = 'draft'

    def set_done(self):
        '''Method to change state to done'''
       
        no_students = self.get_no_students()
        if no_students!=0:
            self.state = 'done'
            self.generate_record_attendance(no_students)
        else:
            raise ValidationError(_( "Error : No hay estudiantes en el curso" ))

    def set_terminate(self):
        '''Set the state to terminate'''
        self.state = 'terminate'

    def set_cancel(self):
        '''Set the state to cancel.'''
        self.state = 'cancel'
#-----------------------------------------------------------------------#
    def set_done_corregir(self):
        '''Method to change state to done - confirm'''
       
        if self.standard_id.state != 'terminate':
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
          contador = len(rec.standard_id.student_ids)

        return contador
#-----------------------------------------------------------------------#
    def generate_record_attendance(self, no_students):
        """Generate registro de asistencia por seccion / Asisnatura."""

        i = 1

        asistencia_obj = self.env['subject.asistencias']

        for rec in self:
            if no_students!=0:
               while i <= no_students:
                   
                   stu_ri    = rec.standard_id.student_ids[i-1].id
                   stu_id    = rec.standard_id.student_ids[i-1].student_id.id
                   stu_state = rec.standard_id.student_ids[i-1].state

                   #raise ValidationError(_( "ENTRO EN GENERAR ri: " + str(stu_ri) + " status:" + stu_state ))
                   #-----------------------------------------------------------------------#
                   # GENRA EL REGISTRO A LOS STUDENT DONE                                  #
                   #-----------------------------------------------------------------------#
                   if stu_state == 'done':
                         asistencia_obj.create({
                            'inscripcion_id': stu_ri,
                            'asistencia_id' : rec.id,
                            'student_id'    : stu_id,
                            
                            'is_attended'   : True,
                            'note'          : " ",
                        })

                   i = i + 1

 #-----------------------------------------------------------------------#
 # DESARROLLO PROPIO: SE AGREGO ESTA CLASE                               #
 #-----------------------------------------------------------------------# 
    
class SubjectAsistencias(models.Model):
    _name = "subject.asistencias"
    _description = "(DETALLE) Registro / Asistencias / Estudiantes"
    _order = "student_id asc"

    inscripcion_id = fields.Many2one('student.inscripcion', string='Registro Inscripciòn', required=True, help='Registro Inscripcion')
    asistencia_id  = fields.Many2one('subject.asistencia',  string="Asistencias", required=True)
    student_id     = fields.Many2one('student.student',     string='Estudiante', required=True, help='Estudiante')
    student_code   = fields.Char("Código", related='student_id.student_code', store=True, help='Código estudiante')
    photo          = fields.Image('Foto', related='student_id.photo', help='Attach student photo')
    
    is_attended    = fields.Boolean('Asistió', default=True, help="Indica la asistencia")
    standard_id = fields.Many2one('school.standard', 'Sección', related='asistencia_id.standard_id', required=True, help='Standard')
    subject_id = fields.Many2one('subject.subject', 'Curso', related='asistencia_id.subject_id', required=True, help='Curso')
    encuentro_id = fields.Many2one('subject.encuentros', 'Encuentro', related='asistencia_id.encuentro_id', required=True, help='Encuentros')
    date_start = fields.Date('Fecha de inicio', related='asistencia_id.date_start', required=True, help='Starting date of Lapso Académico', default=fields.Date.today)
    note = fields.Text('Observaciones', help='Observaciones')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'),
                              ('terminate', 'Terminate'), ('cancel', 'Cancel')], 'Status', related='asistencia_id.state', readonly=True, default="draft",
                              help='State of the student registration form')
#-----------------------------------------------------------------------#
