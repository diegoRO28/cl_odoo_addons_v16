# See LICENSE file for full copyright and licensing details.

from odoo.tools import float_is_zero, float_round, float_repr, float_compare

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _
from lxml import etree
#-----------------------------------------------------------------------#
# DESARROLLO PROPIO: SE AGREGO ESTA CLASE                               #
#-----------------------------------------------------------------------# 
    
class StandardEvaluacion(models.Model):
    _name = "standard.evaluacion"
    _description = "(MAESTRO) Libro de Evaluacion / Evaluaciones "
    _rec_name    = "nombre"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    #-----------------------------------------------------------------------#
    @api.depends('state')
    def _compute_state(self):
        '''Method to compute total student.'''
        for rec in self:
            rec.state_aux = self.get_estado(rec.state)
    #-----------------------------------------------------------------------#

    name          = fields.Char(string='RE Nro.', required=True, copy=False, readonly=True, default=lambda self: _('New'))

    standard_id   = fields.Many2one('school.standard', 'Sección', required=True, help='Standard')
    school_id     = fields.Many2one('school.campus', 'Campus', related='standard_id.school_id', required=True, help='School of the following standard')
    subject_id    = fields.Many2one('subject.subject', 'Curso', required=True, help='Curso')
    libroevas_id  = fields.Many2one('school.libroevas', 'Evaluación', required=True, help='Evaluación')
    teacher_id    = fields.Many2one('school.teacher', 'Profesor', required=True, help='Profesor')
    grade_id      = fields.Many2one('grade.master', 'Escala', related='libroevas_id.libro_id.grade_id', required=True, help='Profesor')
    note          = fields.Text('Observaciones', help='Observaciones')
    note_act      = fields.Text('Actividades', help='Actividades')

    porc_peso     = fields.Integer('% Ponderación', related='libroevas_id.porc_peso', help='Escriba el peso de la evaluación')
    nombre        = fields.Char('Nombre', related='libroevas_id.nombre', help='Escriba el peso de la evaluación')
    is_recupera   = fields.Boolean('¿Acepta recuperación?',  related='libroevas_id.is_recupera', help="Indica la recuperación")
    date_start    = fields.Date('Fecha', required=True, help='Starting date of Lapso Académico', default=fields.Date.today)
    average       = fields.Float('Promedio', help='Promedio de calificación', default=0)

    company_id = fields.Many2one('res.company', 'Companía', related='standard_id.company_id', store=True, help='Company_id of the school')
    
    state_sta   = fields.Selection([('draft', 'Draft'), ('done', 'Done'),('terminate', 'Terminate'), ('cancel', 'Cancel')], 
                             'Status', readonly=True, default="draft", related='standard_id.state', help='State of the student registration form')


    state         = fields.Selection([('draft', 'Draft'), ('done', 'Done'),
                                      ('terminate', 'Terminate'), 
                                      ('recovery', 'Recovery'), 
                                      ('cancel', 'Cancel')], 'Status', readonly=True, default="draft",
                                      tracking=True, help='State of the student registration form')
    
    state_aux     = fields.Selection([('por iniciar', 'Por iniciar'), 
                                         ('iniciado', 'Iniciado'),
                                         ('culminado', 'Culminado'), 
                                         ('recuperado', 'Recuperado'),
                                        ], 'Registro Inscripciòn', readonly=True, default="por iniciar", tracking=True, help='State of the student registration form'
                                        , compute="_compute_state")

    
    evaluacion_ids = fields.One2many('standard.evaluaciones', 'evaluacion_id', string="Registro de Evaluaciones")
    actividad_ids  = fields.One2many('school.libroact', 'evaluacion_id', store=True, help='Students which are in this standard')

#-----------------------------------------------------------------------#
    @api.model
    def create(self, vals):
          if vals.get('name', _('New')) == _('New'):
              vals['name'] = self.env['ir.sequence'].next_by_code('registroeva.code') or _('New')
          res = super(StandardEvaluacion, self).create(vals)
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
        self.asignar_state_evaluacion(True)
        
        self.state = 'terminate'
#-----------------------------------------------------------------------#
    def set_cancel(self):
        '''Set the state to cancel.'''
        self.state = 'cancel'
#-----------------------------------------------------------------------#
    def set_done_corregir(self):
        '''Set the state to cancel.'''
        if self.state_sta != 'terminate':
            self.asignar_state_draft()
            self.state = 'done'
        else:
            raise ValidationError(_( "Error : No se puede volver a iniciado porque la sección está culminada" ))
        
#-----------------------------------------------------------------------#
    def set_recupera(self):
        '''Set the state to terminate'''
        self.registrar_recupera()
        self.asignar_state_evaluacion(False)
        
        self.state = 'recovery'

#-----------------------------------------------------------------------#
    def set_to_terminate(self):
        '''Set the state to terminate'''
        
        self.state = 'terminate'

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
    def get_no_students(self):
        '''Method to compute subjects.'''
        contador = 0
        for rec in self:
             
             line_obj       = rec.standard_id.student_ids
             line_inscritos = line_obj.filtered(lambda x: x.state != "cancel")
             contador       = len(line_inscritos)
        
        #raise ValidationError("no_student:" + str(contador))
        return contador
#-----------------------------------------------------------------------#    
    def get_escala(self):
        '''Method to compute la escala minima.'''

        califica_vals = {'base': 0, 'minimo': 0, 'maximo': 0 , 'aprobado': 0 }
  
        #escalaObj = self.env['grade.line'].sudo().search([('sequence', '=', '1')], limit=1)
        escalaObj = self.grade_id.grade_ids[0]

        if escalaObj:
           califica_vals = {'base'    : escalaObj.base_mark,
                            'minimo'  : escalaObj.from_mark, 
                            'maximo'  : escalaObj.to_mark,
                            'aprobado': escalaObj.pass_mark
                           }
        
        return califica_vals
#-----------------------------------------------------------------------#
    def generate_record_evaluacion(self, no_students):
        """Generate registro de Evaluacion por seccion / Curso."""

        # # Especifica el campo
        # field = "nota1"
        
        #  # Especifica el nombre técnico de la vista
        # view_ref = "school.view_standard_evaluacion_form"

        #     # Carga la vista XML como un objeto
        # view = self.env.ref(view_ref)
        # if not view:
        #         raise ValidationError("La vista {} no existe.".format(view_ref))

        #     # Convierte el campo arch de la vista a un objeto lxml.etree.Element
        # arch_tree = etree.fromstring(view.arch)
        #     # Encuentra el campo price_unit en la vista
        # xpath_expr = "//page/field/tree/field[@name='{}']".format(field)

        # lista_campos = arch_tree.xpath(xpath_expr)
        
        # for field in lista_campos:
        #     field.set("string", "Examen escrito")
        #    # Guarda los cambios en la vista
        # view.write({"arch": etree.tostring(arch_tree)})


        i = 1

        evaluacion_obj = self.env['standard.evaluaciones']
        actividad_obj  = self.env['standard.actividades']


        for rec in self:


            if no_students != 0:

               while i <= no_students:
                   
                   stu_ri    = rec.standard_id.student_ids[i-1].id
                   stu_id    = rec.standard_id.student_ids[i-1].student_id.id
                   stu_state = rec.standard_id.student_ids[i-1].state
                   eva_id    = rec.id


                   no_act    = len(rec.libroevas_id.actividad_ids)

                   if stu_state == 'done':

                        # raise ValidationError(_("Tira: " + stu_state.help))
                        
                        evalua_id = evaluacion_obj.create({
                                            'inscripcion_id': stu_ri,
                                            'evaluacion_id' : eva_id,
                                            'student_id'    : stu_id,
                                        })

                        r=1
                        while r <= no_act:
                            if r==1:
                               evalua_id.is_act1 = True
                               evalua_id.actividad1_id = rec.libroevas_id.actividad_ids[r-1].id
                               rec.note_act = "A1: " + evalua_id.actividad1_id.tipo_id.name + " , "
                               
                            elif r==2:
                               evalua_id.is_act2 = True
                               evalua_id.actividad2_id = rec.libroevas_id.actividad_ids[r-1].id
                               rec.note_act = rec.note_act + " A2: " + evalua_id.actividad2_id.tipo_id.name + " , "
                            elif r==3:
                               evalua_id.is_act3 = True
                               evalua_id.actividad3_id = rec.libroevas_id.actividad_ids[r-1].id
                               rec.note_act = rec.note_act + " A3: " + evalua_id.actividad3_id.tipo_id.name + " , "
                            elif r==4:
                               evalua_id.is_act4 = True
                               evalua_id.actividad4_id = rec.libroevas_id.actividad_ids[r-1].id
                               rec.note_act = rec.note_act + " A4: " + evalua_id.actividad4_id.tipo_id.name + " , "
                               
                            elif r==5:
                               evalua_id.is_act5 = True
                               evalua_id.actividad5_id = rec.libroevas_id.actividad_ids[r-1].id
                               rec.note_act = rec.note_act + " A5: " + evalua_id.actividad5_id.tipo_id.name + " , "
                            elif r==6:
                               evalua_id.is_act6 = True
                               evalua_id.actividad6_id = rec.libroevas_id.actividad_ids[r-1].id
                               rec.note_act = rec.note_act + " A6: " + evalua_id.actividad6_id.tipo_id.name

                            r = r + 1

                          #raise ValidationError("ID : " + str(evalua_id.id))
                  

                   if no_act != 0:

                        j = 1
                        while j <= no_act:
                                
                            act_id = rec.libroevas_id.actividad_ids[j-1].id
                            act_name = rec.libroevas_id.actividad_ids[j-1].nombre
                            #raise ValidationError("GENERANDO LAS EVALUACIONES: while :" + "NO_ACT:" + str(no_act) + "ACT_ID:" + str(act_id) + act_name)
                                #-----------------------------------------------------------------------#
                                # GENERA EL REGISTRO A LOS STUDENT DONE                                  #
                                #-----------------------------------------------------------------------#

                            if stu_state == 'done':
                                         actividad_obj.create({
                                             
                                             'evaluacion_id' : evalua_id.id,
                                             'actividad_id'  : act_id,
                                             'student_id'    : stu_id,
                                         })
                            #raise ValidationError("GENERANDO LAS EVALUACIONES: ..!" + "STU_ID:" + str(stu_id) + "EVA_ID:" + str(rec.id))
                            j = j + 1
                            #raise ValidationError("GENERANDO LAS EVALUACIONES: while :" + "NO_ACT:" + str(no_act) + "ACT_ID:" + str(act_id) + act_name)

                   else:
                        raise ValidationError("ERROR: No hay actividades para la evaluación " + "EVA_ID:" + str(eva_id))

                   i = i + 1

        #raise ValidationError(_("Note: " + rec.note))

#-----------------------------------------------------------------------#
    def get_actividad(self, list_eva):
        """Generate registro de Evaluacion por seccion / Curso."""

        no_actividad  = len(list_eva.actividad_ids)

        i = 1
        while i <= no_actividad:

            if i == 1:
                list_eva.actividad_ids[i-1].nota = list_eva.nota1
            elif i == 2:
                list_eva.actividad_ids[i-1].nota = list_eva.nota2
            elif i == 3:
                list_eva.actividad_ids[i-1].nota = list_eva.nota3
            elif i == 4:
                list_eva.actividad_ids[i-1].nota = list_eva.nota4
            elif i == 5:
                list_eva.actividad_ids[i-1].nota = list_eva.nota5
            elif i == 6:
                list_eva.actividad_ids[i-1].nota = list_eva.nota6

            i = i + 1

#-----------------------------------------------------------------------#
    def asignar_state_evaluacion(self, asigna):
        """asigna: permite registrar la"""
        
        #raise ValidationError("Entro" )
        no_students  = self.get_no_students()
        #raise ValidationError("no_student:" + str(no_students))

        calificaVals = self.get_escala()
        notaT        = 0
        acumN        = 0
        
        for rec in self:

            if no_students != 0:
                i = 1
                while i <= no_students:

                    notaT = self.evaluacion_ids[i-1].nota
                    acumN+=notaT
                    if notaT >= calificaVals['aprobado']:
                        self.evaluacion_ids[i-1].state = "aprobado"
                    else:
                        self.evaluacion_ids[i-1].state = "aplazado"

                    if asigna:
                       self.get_actividad(self.evaluacion_ids[i-1])

                    i = i + 1

                self.average = (acumN/no_students)
                

#-----------------------------------------------------------------------#
    def asignar_state_draft(self):
        """Generate registro de Evaluacion por seccion / Curso."""

        no_students  = self.get_no_students()
        
        for rec in self:

            if no_students != 0:
                i = 1
                while i <= no_students:

                    self.evaluacion_ids[i-1].state = "borrador"

                    i = i + 1

            self.average = 0
            
                
#-----------------------------------------------------------------------#
    def registrar_recupera(self):
        """Generate registro de Evaluacion por seccion / Curso."""

        no_students  = self.get_no_students()
        calificaVals = self.get_escala()
        notaT        = 0
        no_act       = 0
        
        for rec in self:

            if no_students != 0:
                i = 1
                while i <= no_students:

                    j=1
                    no_act  = len(self.evaluacion_ids[i-1].actividad_ids)
                    while j <= no_act:
                        notaR = self.evaluacion_ids[i-1].actividad_ids[j-1].nota_r
                        if j==1 and notaR > 0:
                            self.evaluacion_ids[i-1].nota1 = notaR
                        if j==2 and notaR > 0:
                            self.evaluacion_ids[i-1].nota2 = notaR
                        if j==3 and notaR > 0:
                            self.evaluacion_ids[i-1].nota3 = notaR
                        if j==4 and notaR > 0:
                            self.evaluacion_ids[i-1].nota4 = notaR
                        if j==5 and notaR > 0:
                            self.evaluacion_ids[i-1].nota5 = notaR
                        if j==6 and notaR > 0:
                            self.evaluacion_ids[i-1].nota6 = notaR

                        #raise ValidationError("nota_r : " + str(notaR))
                        j = j + 1
                    
                    i = i + 1
 #-----------------------------------------------------------------------#
 #                                #
 #-----------------------------------------------------------------------# 
    
class StandardEvaluaciones(models.Model):
    _name        = "standard.evaluaciones"
    _description = "(DETALLE) Libro / Evaluaciones / Estudiantes"
    _order       = "student_id asc"

    #-----------------------------------------------------------------------#    
    def get_escala(self):
        '''Method to compute la escala minima.'''

        califica_vals = {'minimo': 0, 'maximo': 0 , 'aprobado': 0 }
  
        escalaObj = self.evaluacion_id.libroevas_id.libro_id.grade_id.grade_ids[0]

        if escalaObj:
           califica_vals = {'minimo'  : escalaObj.from_mark, 
                            'maximo'  : escalaObj.to_mark,
                            'aprobado': escalaObj.pass_mark
                           }
        
        return califica_vals

    #-----------------------------------------------------------------------#    
    def get_peso_act(self, indice):
        '''Method to compute la escala minima.'''

        peso_vals = {'peso': 0 }
  
        actividadObj = self.actividad_ids[indice-1]

        if actividadObj:
           peso_vals = {'peso'  : actividadObj.porc_peso }
        
        return peso_vals

    #-----------------------------------------------------------------------#
    def valida_nota(self,n1,n2,n3,n4,n5,n6):
        calificaVals = self.get_escala()

        er1 = False
        er2 = False
        er3 = False
        er4 = False
        er5 = False
        er6 = False
        error = False

        if (n1 >= calificaVals['minimo']):
            if (n1 <= calificaVals['maximo']):
                er1 = False
            else:
                er1 = True
        else:
            er1 = True

        if (n2 >= calificaVals['minimo']):
            if (n2 <= calificaVals['maximo']):
                er2 = False
            else:
                er2 = True
        else:
            er2 = True

        if (n3 >= calificaVals['minimo']):
            if (n3 <= calificaVals['maximo']):
                er3 = False
            else:
                er3 = True
        else:
            er3 = True

        if (n4 >= calificaVals['minimo']):
            if (n4 <= calificaVals['maximo']):
                er4 = False
            else:
                er4 = True
        else:
            er4 = True

        if (n5 >= calificaVals['minimo']):
            if (n5 <= calificaVals['maximo']):
                er5 = False
            else:
                er5 = True
        else:
            er5 = True

        if (n6 >= calificaVals['minimo']):
            if (n6 <= calificaVals['maximo']):
                er6 = False
            else:
                er6 = True
        else:
            er6 = True

        if er1 or er2 or er3 or er4 or er5 or er6:
           error = True
        else:
            error = False

        return error
    #-----------------------------------------------------------------------#

    inscripcion_id = fields.Many2one('student.inscripcion', string='Registro Inscripciòn', required=True, help='Registro Inscripcion')
    evaluacion_id  = fields.Many2one('standard.evaluacion', string="Evaluaciones", required=True)
    student_id     = fields.Many2one('student.student',     string='Estudiante', required=True, help='Estudiante')
    student_code   = fields.Char("Código", related='student_id.student_code', store=True, help='Total Evaluaciones')
 
    nombre_eva     = fields.Char('Nombre', related='evaluacion_id.nombre', help='Escriba el nombre ')
    porc_peso      = fields.Integer("% Ponderación", related='evaluacion_id.porc_peso', store=True, help='Total Evaluaciones')
    is_recupera    = fields.Boolean('¿Acepta recuperación?', related='evaluacion_id.is_recupera', default=True, help="Indica la recuperación")
    photo = fields.Image('Foto', related='student_id.photo', help='Attach student photo')

    nota           = fields.Float('Calificación', help='Escriba la calificación', default=0, compute='_compute_nota', digits='0')

    note           = fields.Text('Observaciones', help='Observación')
    state          = fields.Selection([('borrador', 'Borrador'), 
                                       ('aprobado', 'Aprobado'),
                                       ('aplazado', 'Aplazado'), 
                                       ('inasistente', 'Inasistente'),
                                      ], 'Status', readonly=True, default="borrador", help='State of the student registration form')

    state_aux        = fields.Selection([('por iniciar', 'Por iniciar'), 
                                         ('iniciado', 'Iniciado'),
                                         ('culminado', 'Culminado'), 
                                        ], 'Registro Inscripciòn', readonly=True, default="por iniciar", related='evaluacion_id.state')
    
    state_inc        = fields.Selection([('preinscrito', 'Preinscrito'), 
                                         ('inscrito', 'Inscrito'),
                                         ('culminado', 'Culminado'), 
                                         ('retirado', 'Retirado'),
                                        ], 'Status', readonly=True, default="por iniciar", related='inscripcion_id.state',help='State of the student registration form'
                                        )

    actividad_ids = fields.One2many('standard.actividades', 'evaluacion_id', string="Registro de Evaluaciones")

    nota1          = fields.Float('Act1', help='Escriba la calificación', default=0)
    nota2          = fields.Float('Act2', help='Escriba la calificación', default=0)
    nota3          = fields.Float('Act3', help='Escriba la calificación', default=0)
    nota4          = fields.Float('Act4', help='Escriba la calificación', default=0)
    nota5          = fields.Float('Act5', help='Escriba la calificación', default=0)
    nota6          = fields.Float('Act6', help='Escriba la calificación', default=0)

    is_act1        = fields.Boolean('IS act1?', default=False, help="Indica la recuperación")
    is_act2        = fields.Boolean('IS act1?', default=False, help="Indica la recuperación")
    is_act3        = fields.Boolean('IS act1?', default=False, help="Indica la recuperación")
    is_act4        = fields.Boolean('IS act1?', default=False, help="Indica la recuperación")
    is_act5        = fields.Boolean('IS act1?', default=False, help="Indica la recuperación")
    is_act6        = fields.Boolean('IS act1?', default=False, help="Indica la recuperación")

    actividad1_id  = fields.Many2one('school.libroact', string="Actividad")
    actividad2_id  = fields.Many2one('school.libroact', string="Actividad")
    actividad3_id  = fields.Many2one('school.libroact', string="Actividad")
    actividad4_id  = fields.Many2one('school.libroact', string="Actividad")
    actividad5_id  = fields.Many2one('school.libroact', string="Actividad")
    actividad6_id  = fields.Many2one('school.libroact', string="Actividad")

#-----------------------------------------------------------------------#
#                  WRITE                                                #
#-----------------------------------------------------------------------# 
    # def write(self, vals):

    #     acumNota   = 0.00
    #     n1         = 0.00
    #     n2         = 0.00
    #     n3         = 0.00
    #     n4         = 0.00
    #     n5         = 0.00
    #     n6         = 0.00

    #     #no_act     = len(self.evaluacion_id.evaluacion_id.actividad_ids)

    #     er1         = self.valida_nota(vals.get('nota1'))
    #     er2         = self.valida_nota(vals.get('nota2'))
    #     er3         = self.valida_nota(vals.get('nota3'))
    #     # er4         = self.valida_nota(vals.get('nota4'))
    #     # er5         = self.valida_nota(vals.get('nota5'))

    #     if er1 or er2 or er3:
    #         raise ValidationError(_( "Error : La calificaciòn debe estar entre 0..20 " ))
    #     # else:
            
    #     #     n1         = vals.get('nota1')
    #     #     n2         = vals.get('nota2')
    #     #     n3         = vals.get('nota3')
    #     #     n4         = vals.get('nota4')
    #     #     n5         = vals.get('nota5')

        #     acumNota   = n1 + n2 + n3

        #     vals['nota'] = acumNota
                
        #return super(StandardEvaluaciones, self).write(vals)
#-----------------------------------------------------------------------#   
    @api.depends('nota1', 'nota2', 'nota3', 'nota4', 'nota5','nota6')
    def _compute_nota(self):
        """
        Compute the amounts of the SO line.
        """

        #tira = "N1=" + str(self.nota1) + " N2=" + str(self.nota2) + " N3=" + str(self.nota3) + " N4=" + str(self.nota4) + " N5=" + str(self.nota5) + " N6=" + str(self.nota6)
        
        #raise ValidationError(_( "Tira : " + tira ))
    
        no_actividad  = len(self.actividad_ids)

        notaTotal = 0
        pesoTotal = 0
        error     = False

        pesoAct1  = 0
        pesoAct2  = 0
        pesoAct3  = 0
        pesoAct4  = 0
        pesoAct5  = 0
        pesoAct6  = 0

        porcAct1  = 0
        porcAct2  = 0
        porcAct3  = 0
        porcAct4  = 0
        porcAct5  = 0
        porcAct6  = 0

        for line in self:
            error  = self.valida_nota(line.nota1,line.nota2,line.nota3,line.nota4,line.nota5,line.nota6)
            if error:
               raise ValidationError(_( "Error : La calificaciòn debe estar entre 0..20 " ))
            else:
                if no_actividad >= 1:
                   porcAct1 = self.get_peso_act(1)
                   pesoAct1 = float(float(line.nota1) / 20) * float(porcAct1['peso'])

                if no_actividad >= 2:
                   porcAct2 = self.get_peso_act(2)
                   pesoAct2 = float(float(line.nota2) / 20) * float(porcAct2['peso'])

                if no_actividad >= 3:
                   porcAct3 = self.get_peso_act(3)
                   pesoAct3 = float(float(line.nota3) / 20) * float(porcAct3['peso'])

                if no_actividad >= 4:
                   porcAct4 = self.get_peso_act(4)
                   pesoAct4 = float(float(line.nota4) / 20) * float(porcAct4['peso'])

                if no_actividad >= 5:
                   porcAct5 = self.get_peso_act(5)
                   pesoAct5 = float(float(line.nota5) / 20) * float(porcAct5['peso'])

                if no_actividad >= 6:
                   porcAct6 = self.get_peso_act(6)
                   pesoAct6 = float(float(line.nota6) / 20) * float(porcAct6['peso'])

                pesoTotal = pesoAct1 + pesoAct2 + pesoAct3 + pesoAct4 + pesoAct5 + pesoAct6

                notaTotal = float_round( ((pesoTotal * 20 ) / 100) ,2 )

                line.update({'nota': notaTotal})

 #-----------------------------------------------------------------------#
 #                                #
 #-----------------------------------------------------------------------# 
    
class StandardActividades(models.Model):
    _name        = "standard.actividades"
    _description = "(DETALLE) Libro / Evaluaciones / Estudiantes / Actividades"
    #_order       = "student_id asc"
    
    actividad_id   = fields.Many2one('school.libroact',     string="Actividades", required=True)
    nombre         = fields.Char('Nombre', related='actividad_id.nombre', help='Escriba el Nombre')
    student_id     = fields.Many2one('student.student', string='Estudiante', required=True, help='Estudiante')

    porc_peso      = fields.Integer("% Ponderación", related='actividad_id.porc_peso', store=True, help='Total Evaluaciones')
    is_recupera    = fields.Boolean('¿Acepta recuperación?', related='actividad_id.is_recupera', default=True, help="Indica la recuperación")

    nota           = fields.Float('Calificación', help='Escriba la calificación', default=0)
    nota_r         = fields.Float('Recuperación', help='Escriba la calificación', default=0)
    recupera_date  = fields.Date(string="Fecha de recuperación", required=True, default=fields.Date.today)
    note           = fields.Text('Observaciones', help='Observación')
    state          = fields.Selection([('borrador', 'Borrador'), 
                                       ('aprobado', 'Aprobado'),
                                       ('aplazado', 'Aplazado'), 
                                       ('inasistente', 'Inasistente'),
                                      ], 'Calificaciòn', readonly=True, default="borrador", help='State of the student registration form')

    evaluacion_id  = fields.Many2one('standard.evaluaciones', string="Evaluaciones", required=True)

#-----------------------------------------------------------------------#
