# See LICENSE file for full copyright and licensing details.

# import time
import calendar
import re

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.translate import _

EM = (r"[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$")

class SchoolStandard(models.Model):
    '''Defining a standard related to school.'''

    _name        = 'school.standard'
    _description = 'School Standards / SECCIONES'
    _rec_name    = "code"
    _order       = "school_id, code"
    _inherit     = ['mail.thread', 'mail.activity.mixin']

    # @api.depends('standard_id', 'school_id', 'division_id', 'medium_id', 'school_id')
    # def _compute_student(self):
    #     '''Compute student of done state'''
    #     student_obj = self.env['school.estudiante']
    #     for rec in self:
    #         rec.student_ids = student_obj.\
    #             search([('standard_id', '=', rec.id),
    #                     ('school_id', '=', rec.school_id.id),
    #                     ('state', '=', 'done')])

    def get_no_eva_terminate(self):
        '''Method to change state to draft'''

        contaTerminate = 0
        acumTerminate  = 0
        i              = 1

        no_evas = len(self.registroeva_ids)

        while i <= no_evas:
            if self.registroeva_ids[i-1].state == "terminate":
                contaTerminate += 1
                acumTerminate  += self.registroeva_ids[i-1].porc_peso
            i+= 1

        self.total_evas_terminate = contaTerminate
        self.porc_evas_terminate  = acumTerminate


    # def get_porc_eva_terminate(self):
    #     '''Method to change state to draft'''
    #     acumTerminate   = 0
    #     i       = 1
    #     no_evas = self.total_evas

    #     while i <= no_evas:
    #         if self.registroeva_ids[i-1].state == "terminate":
    #             acumTerminate += self.registroeva_ids[i-1].porc_peso
    #         i+= 1

    #     return acumTerminate

    @api.depends('subject_ids')
    def _compute_subject(self):
        '''Method to compute subjects.'''
        for rec in self:
            rec.total_no_subjects = len(rec.subject_ids)

    @api.depends('student_ids','total_students_cancel')
    def _compute_total_student(self):
        '''Method to compute total student.'''
        for record in self:
            
            line_obj    = record.student_ids
            line_cancel = line_obj.filtered(lambda x: x.state in ['cancel'])
            line_done   = line_obj.filtered(lambda x: x.state in ['done'])

            no_cancel   = len(line_cancel)
            no_done     = len(line_done)
        
            record.total_students        = no_done
            record.total_students_cancel = no_cancel
            record.remaining_seats       = record.capacity - no_done
            #raise ValidationError(_( "Estoy en total_student" ))


    @api.depends("capacity", "total_students", "total_students_cancel")
    def _compute_remain_seats(self):
        '''Method to compute remaining seats.'''
        for rec in self:
            
            rec.remaining_seats = rec.capacity - rec.total_students 

    @api.depends('registroeva_ids')
    def _compute_total_evas(self):
        '''Method to compute total evaluaciones.'''
        for rec in self:
            rec.total_evas     = len(rec.registroeva_ids)

    @api.depends('total_evas_terminate')
    def _compute_total_evas_terminate(self):
        '''Method to compute total evaluaciones.'''
        for rec in self:
            rec.porc_terminate = rec.get_eva_terminate()

    @api.depends('state')
    def _compute_state(self):
        '''Method to compute total student.'''
        for rec in self:
            rec.state_aux = self.get_estado(rec.state)

    name = fields.Char(string='SEC Nro.', required=True, copy=False, readonly=True, default=lambda self: _('New'))

    code = fields.Char('Código', states={'terminate': [('readonly', True)]}, help='Código de la sección')
    school_id = fields.Many2one('school.campus', 'Campus', required=True, states={'terminate': [('readonly', True)]}, help='School of the following standard')
    standard_id = fields.Many2one('standard.standard', 'Nivel', required=True, states={'terminate': [('readonly', True)]}, help='Standard')
    division_id = fields.Many2one('standard.division', 'Turno', required=True, states={'terminate': [('readonly', True)]}, help='Standard division')
    medium_id = fields.Many2one('standard.medium', 'Modalidad', required=True, states={'terminate': [('readonly', True)]}, help='Medium of the standard')
    subject_id = fields.Many2one('subject.subject', 'Curso', required=True, states={'terminate': [('readonly', True)]}, help='Curso')

    grade_id    = fields.Many2one('grade.master', 'Escala', related='subject_id.libro_id.grade_id', required=True, help='Escala')

    subject_ids = fields.Many2many('subject.subject', 'subject_standards_rel', 'subject_id', 'standard_id', 'Subject', help='Subjects of the standard')
    
    user_id = fields.Many2one('school.teacher', 'Profesor',required=True, states={'terminate': [('readonly', True)]}, help='Teacher of the standard')

    student_ids = fields.One2many('student.inscripcion', 'standard_id', 'Estudiantes Inscritos', store=True, help='Students which are in this standard')
    asistencia_ids = fields.One2many('subject.asistencia', 'standard_id', 'Encuentros', store=True, help='Students which are in this standard')
    evaluacion_ids = fields.One2many('subject.evaluacion', 'standard_id', 'Evaluaciones', store=True, help='Students which are in this standard')

    color = fields.Integer('Color Index', help='Index of color')
    cmp_id = fields.Many2one('res.company', 'Company Nombre', required=True,store=True, help='Company_id of the school')

    # syllabus_ids = fields.One2many('subject.syllabus', 'standard_id',
    #                                'Syllabus',
    #                                help='Syllabus of the following standard')
    total_no_subjects = fields.Integer('Total No of Subject', compute="_compute_subject", help='Total subjects in the standard')
    #name = fields.Char('Nombre', help='Standard name')
    capacity = fields.Integer("Capacidad", states={'terminate': [('readonly', True)]}, help='Standard capacity')
    total_students = fields.Integer("Total Inscritos", compute="_compute_total_student", store=True, help='Total students of the standard')
    total_students_cancel = fields.Integer("Total Retirados", compute="_compute_total_student", store=True, help='Total students cancel of the standard')

    total_evas     = fields.Integer("Total Evaluaciones", compute="_compute_total_evas", store=True, help='Total evaluaciones de la sección')
    total_evas_terminate = fields.Integer("Total Evaluaciones Culminadas", compute="_compute_total_evas", store=True, help='Total evaluaciones de la sección')
    porc_evas_terminate  = fields.Float('% Evaluado', help='% Ejecutado', default=0)

    remaining_seats = fields.Integer("Cupos Disponibles", compute="_compute_remain_seats", store=True, help='Remaining seats of the standard')
    class_room_id = fields.Many2one('class.room', 'Salón de Clases', required=True, states={'terminate': [('readonly', True)]}, help='Class room of the standard') 
    note = fields.Text('Horario de Clases', states={'terminate': [('readonly', True)]}, help='Horario')

    average_o    = fields.Float('Evaluaciòn Oral', help='Escriba la evaluación Oral', default=0)
    average_e    = fields.Float('Evaluaciòn Escrita', help='Escriba la evaluación Oral', default=0)
    average_t    = fields.Float('Total', help='Escriba la evaluación Oral', default=0)
    average      = fields.Float('Promedio', help='Promedio de calificaciones de la sección', default=0)

    state = fields.Selection([('draft', 'Draft'), 
                              ('done', 'Done'),
                              ('terminate', 'Terminate'), 
                              ('cancel', 'Cancel')], 
                             'Status', readonly=True, default="draft", tracking=True, help='State of the student registration form')
    
    state_aux        = fields.Selection([('por iniciar', 'Por iniciar'), 
                                         ('iniciado', 'Iniciado'),
                                         ('culminado', 'Culminado'), 
                                        ], 'Status', readonly=True, default="por iniciar", tracking=True, help='State of the student registration form'
                                        , compute="_compute_state")
    #-----------------------------------------------------------------------#
    # V2                                                                    #
    #-----------------------------------------------------------------------# 
    libro_id        = fields.Many2one('school.libroeva', 'Libro Evaluación', related='subject_id.libro_id', help='''Seleccione el libro de evaluación''')
    registroeva_ids = fields.One2many('standard.evaluacion', 'standard_id', 'Evaluaciones', store=True, help='Students which are in this standard')
    company_id      = fields.Many2one('res.company', 'Companía', related='school_id.company_id', store=True, help='Company_id of the school')
    start_date      = fields.Date('Fecha de inicio', required=True, states={'terminate': [('readonly', True)]}, help='Starting date of Lapso Académico', default=fields.Date.today)
    end_date        = fields.Date('Fecha de finalización', required=True, states={'terminate': [('readonly', True)]}, help='End date of Lapso Académico')
    code_moodle     = fields.Char(string='Código Moodle', required=True, store=True)
    cmp_id          = fields.Many2one('res.company', 'Company cmp',  related='school_id.company_id')

    @api.model
    def create(self, vals):
          if vals.get('name', _('New')) == _('New'):
              vals['name'] = self.env['ir.sequence'].next_by_code('seccion.code') or _('New')
          res = super(SchoolStandard, self).create(vals)
          return res

    def set_draft(self):
        '''Method to change state to draft'''
        self.state = 'draft'

    def set_done(self):
        '''Method to change state to done'''
        
        if self.total_students > 0:
             self.state = 'done'
             self.generate_encuentros()
             self.generate_registroEva()
        else:
             raise ValidationError(_( "Error : No hay Estudiantes inscritos en la Secciòn" ))
        
    def set_done_corregir(self):
        '''Method to change state to done'''
        
        if self.subject_id:
             self.asignar_state_corregir()
             self.state = 'done'
             #self.generate_encuentros()
             #self.generate_evaluaciones()
 

    def set_terminate(self):
        '''Set the state to terminate'''
        
        if self.validar_evaluaciones() and self.validar_encuentros():
           self.calcular_promedios(True)
           self.state = 'terminate'
        else:
           raise ValidationError(_( "Error : No se puede cerrar la secciòn. Hay encuentros o evaluaciones pendiantes por realizar" ))

    def set_cancel(self):
        '''Set the state to cancel.'''
        self.state = 'cancel'

    def set_avance(self):
        '''Set the state to done'''
        self.get_no_eva_terminate()
        #self.porc_evas_terminate = self.get_porc_eva_terminate()
        self.calcular_promedios(False)

    def set_genera_reg_eva(self):
        '''Set the state to done'''
        
        if self.total_students > 0 and len(self.registroeva_ids) == 0:
            
             self.generate_registroEva()
        else:
             raise ValidationError(_( "Error : No hay Estudiantes inscritos en la Secciòn o ya se generó el registro de evaluaciones" ))
#------------------------------------------------------------------------------#
#   METODO PARA GENERAR EL REGISTRO DE ASISTENCIAS LUEGO DE ABIERTA LA SECCION #
#------------------------------------------------------------------------------#
    def set_genera_reg_asi(self):
        '''Set the state to done'''
        
        if self.total_students > 0 and len(self.asistencia_ids) == 0:
             
             self.generate_encuentros()
        else:
             raise ValidationError(_( "Error : No hay Estudiantes inscritos en la Secciòn o ya se generó el registro de asistencias" ))




    def actualizar_name(self):
        '''Method to confirm admission'''
        
        student_obj = self.student_ids

        i      = 1
        no_stu = len(self.student_ids)
        aux = ""
        while i <= no_stu:
            aux = student_obj[i-1].student_id.middle
            if not aux:
               student_obj[i-1].student_id.middle = student_obj[i-1].student_id.name
              

            if not student_obj[i-1].student_id.last:
               student_obj[i-1].student_id.last = student_obj[i-1].student_id.name
            
            i = i + 1

        # raise UserError(_(
        #                 "Actualizo: " + str(i)))
    

    #-----------------------------------------------------------------------#
    def get_estado(self , sta):
        '''Method to compute la escala minima.'''

        if sta == 'draft':
           return 'por iniciar'
        elif sta == 'done':
           return 'iniciado' 
        elif sta == 'terminate':
           return 'culminado'
        elif sta == 'recovery':
           return 'recuperado'
        
        else:
            return sta
        
        return sta    
    
   #-----------------------------------------------------------------------#
   # DESARROLLO PROPIO: SE AGREGO ESTE METODO                              #
   #-----------------------------------------------------------------------#  
    # @api.onchange('code')
    # def _onchange_code(self):
    #     if not self.code:
    #         return
        
    #     self.code = self.code.upper()

    #     digito = self.code.isalnum()
    #     if not digito:
    #         aux = self.code
            
    #         return {'warning': {
    #             'title': ("Mensaje de Error:"), 
    #             'message': ("Error: El código de la sección debe contener sólo valores alfanumérico..! "), 
    #         }}
        
    #     if len(self.code) > 3:
    #         aux = self.code
            
    #         return {'warning': {
    #             'title': ("Mensaje de Error:"), 
    #             'message': ("Error: El còdigo de la secciòn debe contener hasta 3 caracteres..! "),  
    #         }}
    #-----------------------------------------------------------------------#    
    def get_no_subjects(self):
        '''Method to compute subjects.'''
        contador = 0
        for rec in self:
             #nombre = rec.standard_id.student_ids[0].student_code
             contador = len(rec.subject_ids)

        return contador
    
    #-----------------------------------------------------------------------#
     
    def get_escala(self):
        '''Method to compute la escala minima.'''

        califica_vals = {'base': 0, 'minimo': 0, 'maximo': 0 , 'aprobado': 0 }
   
        # escalaObj = self.env['grade.line'].sudo().search([('sequence', '=', '1')], limit=1)
        escalaObj = self.grade_id.grade_ids[0]

        if escalaObj:
           califica_vals = {'base'    : escalaObj.base_mark, 
                            'minimo'  : escalaObj.from_mark,
                            'maximo'  : escalaObj.to_mark,
                            'aprobado': escalaObj.pass_mark
                           }
        
        return califica_vals
    
    #-----------------------------------------------------------------------#
    def asignar_state_corregir(self):
        """Generate registro para correccion"""
 
        i      = 1
        no_stu = len(self.student_ids)
        
        while i <= no_stu:

            self.student_ids[i-1].state_eva = 'borrador'
            self.student_ids[i-1].eva_o = 0
            self.student_ids[i-1].eva_e = 0
            self.student_ids[i-1].eva_t = 0
            
            if self.student_ids[i-1].state == 'terminate':
                self.student_ids[i-1].state = 'done'
                
            i = i + 1
    
    #-----------------------------------------------------------------------#   
    def generate_encuentros(self):
        """Generate Encuentros por seccion / Curso."""

        no_encuentros = 0

        asistencia_obj = self.env['subject.asistencia']

        for rec in self:
            
          sta_id = rec.id
          use_id = rec.user_id.id
          sub_id = rec.subject_id.id
          no_encuentros = len(rec.subject_id.encuentro_ids)
          
          if no_encuentros == 0:
            raise ValidationError(_("Error: El curso tiene 0 Encuentros. Acuda al administrador del sistema."))
          else:
            j = 1

            while j <= no_encuentros:
                            
                enc_id   = rec.subject_id.encuentro_ids[j-1].id
                aux_desc = rec.subject_id.encuentro_ids[j-1].description

                asistencia_obj.create({
                                    'standard_id' : sta_id,
                                    'subject_id'  : sub_id,
                                    'teacher_id'  : use_id,
                                    'encuentro_id': enc_id,
                                    'note' : aux_desc,
                                    })
                j = j + 1
                     
    #-----------------------------------------------------------------------# 
    # GENERA LAS EVALUACIONES#
    #-----------------------------------------------------------------------#
    def generate_evaluaciones(self):
        """Generate Encuentros por seccion / Curso."""

        no_eva = 0

        evaluacion_obj = self.env['subject.evaluacion']

        for rec in self:
                    
          sta_id = rec.id
          use_id = rec.user_id.id
          sub_id = rec.subject_id.id
          no_eva = len(rec.subject_id.evaluacion_ids)
          j = 1

          while j <= no_eva:
            enc_id = rec.subject_id.evaluacion_ids[j-1].id
            aux_desc = rec.subject_id.evaluacion_ids[j-1].description
            evaluacion_obj.create({
                                   'standard_id'  : sta_id,
                                   'subject_id'   : sub_id,
                                   'teacher_id'   : use_id,
                                   'evaluacion_id': enc_id,
                                   'note'  : aux_desc,
                                  })
            j = j + 1

    #-----------------------------------------------------------------------# 
    # GENERA LAS EVALUACIONES#
    #-----------------------------------------------------------------------#
    def generate_registroEva(self):
        """Generate Encuentros por seccion / Curso."""

        no_eva = 0

        evaluacion_obj = self.env['standard.evaluacion']

        for rec in self:
                    
          sta_id = rec.id
          use_id = rec.user_id.id
          sub_id = rec.subject_id.id
          no_eva = len(rec.subject_id.libroevas_ids)

          tira = ""
          
          j = 1

          while j <= no_eva:

            eva_id   = rec.subject_id.libroevas_ids[j-1].id
            aux_note = rec.subject_id.libroevas_ids[j-1].note
            #tira     = tira + rec.subject_id.libroevas_ids[j-1].nombre + " ID (" + str(eva_id) + ") "+ " ; "
            #tira     = tira + rec.subject_id.libroevas_ids[j-1].actividad_ids[0].nombre + " ID (" + str(eva_id) + ") "+ " ; "
            #actObj   = rec.subject_id.libroevas_ids[j-1]
            #actObj[j-1].actividad_ids  = rec.subject_id.libroevas_ids[j-1].actividad_ids

            #no_act   = len(actObj)

            #i = 1
            # while i <= no_act:
            #     actObj[j-1].actividad_ids[i-1] = rec.subject_id.libroevas_ids[j-1].actividad_ids[i-1]
            #     tira = tira + " Act (" + str(actObj[i-1].id) + ") " + actObj[i-1].nombre + " ; " + actObj[i-1].actividad_ids[i-1].nombre+ " ; "
            #     i = i + 1
            #raise ValidationError(_("Tira: " + tira))
            evaluacion_obj.create({
                                   'standard_id'  : sta_id,
                                   'subject_id'   : sub_id,
                                   'teacher_id'   : use_id,
                                   'libroevas_id' : eva_id,
                                   'note'         : aux_note,
                                   
                                  })

            j = j + 1
            
        #raise ValidationError(_("Tira: " + tira))

            
    #-----------------------------------------------------------------------# 
    # VALIDA QUE LAS EVALUACIONES FUERON REALIZADOS                         #
    #-----------------------------------------------------------------------#
    def validar_evaluaciones(self):
         
         auxTerminate = True
         no_eva       = 0
         j            = 1
         no_eva       = len(self.registroeva_ids)
         
         while j <= no_eva:
            auxState = self.registroeva_ids[j-1].state

            if auxState != 'terminate':
               auxTerminate = False

            j = j + 1

         return auxTerminate
    
    #-----------------------------------------------------------------------# 
    # VALIDA QUE LOS ENCUANTROS FUERON REALIZADOS                           #
    #-----------------------------------------------------------------------#
    def validar_encuentros(self):
         
         auxTerminate = True
         no_eva       = 0
         j            = 1
         no_eva       = len(self.asistencia_ids)
         
         while j <= no_eva:
            auxState = self.asistencia_ids[j-1].state

            if auxState != 'terminate':
               auxTerminate = False

            j = j + 1

         return auxTerminate
    
    #-----------------------------------------------------------------------# 
    # CALCULA LAS EVALUACIONES QUE FUERON REALIZADAS                        #
    #-----------------------------------------------------------------------#
    def cantidad_evaluacion_cerrada(self):
         
         no_eva       = 0
         j            = 1
         contaDone    = 0
         no_eva       = len(self.evaluacion_ids)
         
         while j <= no_eva:
            auxState = self.evaluacion_ids[j-1].state

            if auxState == 'done':
               contaDone = contaDone + 1

            j = j + 1

         return contaDone

    #-----------------------------------------------------------------------# 
    # CALCULA LOSS PROMEDIOS DE LA SECCION Y DE LOS ESTUDIANTES             #
    #-----------------------------------------------------------------------#
    def calcular_promedios(self,sw):

         calificaVals   = self.get_escala()
         baseEscala     = calificaVals['base']
         pesoEva        = 0
         acumNota       = 0
         contaTerminate = 0
         acumTotalNota  = 0
         
         auxTerminate = True
         
         acumNotaStu = 0

         acumOral = 0
         acumEsc  = 0
         contaEva = 0

         
         acumOralStu = 0
         acumEscStu = 0

         no_stu       = 0
         no_eva       = 0
         i            = 1
         j            = 1
         r            = 1

         no_stu       = len(self.student_ids)
         no_eva       = len(self.registroeva_ids)
         contaStu     = 0
         
         #raise ValidationError(_( "no_student: " + str(no_eva) ))

         # CICLO GENERAL
         while i <= no_stu:

            acumNota = 0

            auxStu   = self.student_ids[i-1].student_id.id
            
            j         = 1

            if self.student_ids[i-1].state != 'cancel':

               contaStu       = contaStu + 1
               acumNota       = 0
               contaTerminate = 0

               # CICLO EVALUACION
               while j <= no_eva:
                        auxEva = self.registroeva_ids[j-1].id

                        if self.registroeva_ids[j-1].state == 'terminate':

                            pesoEva         = self.registroeva_ids[j-1].porc_peso
                            
                            nombreEva       = self.registroeva_ids[j-1].nombre
                            contaTerminate += 1

                            no_evas = len(self.registroeva_ids[j-1].evaluacion_ids)
                            r = 1

                            # CICLO EVALUACIONES
                            while r <= no_evas:
                                if auxStu == self.registroeva_ids[j-1].evaluacion_ids[r-1].student_id.id:

                                    notaEva      = self.registroeva_ids[j-1].evaluacion_ids[r-1].nota

                                    if baseEscala > 0:
                                        porcNota     = ( notaEva / baseEscala ) * 100

                                    porcPesoNota = (pesoEva * porcNota ) / 100
                                    
                                    if baseEscala > 0:
                                        notaTotal    = (porcPesoNota * baseEscala) / 100         

                                    acumNota    += notaTotal   

                                    #raise ValidationError(_( "Eva : " + nombreStu + " " + nombreEva + " Nota :" + str(notaTotal) ))

                                r = r + 1

                        j = j + 1
            
               if contaTerminate > 0:

                    porcTerminate = (self.porc_evas_terminate * baseEscala) / 100

                    if porcTerminate > 0:
                        porcAlcanzado = (acumNota / porcTerminate) * 100

                    if baseEscala > 0:
                        self.student_ids[i-1].nota = (porcAlcanzado * baseEscala) / 100

                    if self.student_ids[i-1].state != 'cancel':
                            
                        
                            if self.student_ids[i-1].nota >= calificaVals['aprobado']:
                                    self.student_ids[i-1].state_eva = 'aprobado'
                            else:
                                    self.student_ids[i-1].state_eva = 'aplazado'
                        
                        
                            if sw:
                                self.student_ids[i-1].state = 'terminate'
                                self.student_ids[i-1].student_id.state = 'terminate'
                            else:
                                self.student_ids[i-1].state = 'done'
                                self.student_ids[i-1].student_id.state = 'done'

                    acumTotalNota += self.student_ids[i-1].nota
 
            else:
                self.student_ids[i-1].nota = 0
                

            i = i + 1

         if contaStu > 0:
             self.average = (acumTotalNota / contaStu)
         else:
             self.average = 0
             

         return auxTerminate
   #-----------------------------------------------------------------------# 

    @api.onchange('standard_id', 'division_id')
    def onchange_combine(self):
        '''Onchange to assign name respective of it's standard and division'''
        #self.name = str(self.standard_id.name ) + '-' + str(self.division_id.name)

    #@api.constrains('standard_id', 'division_id')
    #def check_standard_unique(self):
    #    """Method to check unique standard."""
    #    if self.env['school.standard'].search([
    #                            ('standard_id', '=', self.standard_id.id),
    #                            ('division_id', '=', self.division_id.id),
    #                            ('school_id', '=', self.school_id.id),
    #                            ('id', 'not in', self.ids)]):
    #        raise ValidationError(_("Division and class should be unique!"))

    @api.constrains('standard_id', 'division_id')
    def check_standard_unique(self):
        """Method to check unique standard."""
        if self.env['school.standard'].search([
                                
                                ('code', '=', self.code),
                                ('school_id', '=', self.school_id.id),
                                ('id', 'not in', self.ids)]):
            raise ValidationError(_("El còdigo de la secciòn debe ser ùnico en el campus!"))
  
    # def unlink(self):
    #     """Method to check unique standard."""
    #     for rec in self:
    #         if rec.student_ids or rec.subject_ids or rec.syllabus_ids:
    #             raise ValidationError(_(
    # "You cannot delete as it has reference with student, subject or syllabus!"))
    #     return super(SchoolStandard, self).unlink()

    @api.constrains('capacity')
    def check_seats(self):
        """Method to check seats."""
        if self.capacity <= 0:
            raise ValidationError(_("Total seats should be greater than 0!"))

    def name_get(self):
        '''Method to display standard and division'''
        #return [(rec.id, rec.standard_id.name + '-' + '[' + rec.division_id.name + ']' + '[' + rec.code + ']') for rec in self]
        #return [(rec.id, rec.code + '-' + '[' + rec.subject_id.nombre + ']'+ '-' + '[' + rec.name + ']' ) for rec in self]
        return [(rec.id, rec.code + '/' + rec.subject_id.code ) for rec in self]

