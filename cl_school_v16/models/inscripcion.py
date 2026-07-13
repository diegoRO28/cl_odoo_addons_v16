# See LICENSE file for full copyright and licensing details.



from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.translate import _

PAYMENT_STATE_SELECTION = [
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
]

SOLVENCIA_STATE_SELECTION = [
        ('solvente', 'Solvente'),
        ('insolvente', 'Insolvente'),
        ('anulada', 'Anulada'),
]

class StudentInscripcion(models.Model):
    '''Defining a student inscripcion.'''

    _name = 'student.inscripcion'
    _description = 'Student Inscripcion'
    _order = "inscription_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']
 
    @api.constrains('student_id')
    def _check_code(self):
         for record in self:
             domain = [('id', '!=', record.id), ('student_id', '=' , record.student_id.id), ('standard_id', '=' , record.standard_id.id)]
             if self.env["student.inscripcion"].search(domain):
                raise ValidationError("Error: El estudiante ya està inscrito en la SECCIÒN..!")
    
    @api.constrains('standard_id')
    def _check_cupo(self):
         for record in self:
            if self.standard_id.remaining_seats<=0:
                raise ValidationError("Error: La sección no tiene cupos disponibles..! " + " seccion : " + str(self.standard_id.code) + "Seats: " + str(self.standard_id.remaining_seats))           
    
    @api.depends('state')
    def _compute_state(self):
        '''Method to compute total student.'''
        for rec in self:
            rec.state_aux = self.get_estado(rec.state)

    name             = fields.Char(string='RI Nro.', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    #student_id      = fields.Many2one('school.estudiante', 'Estudiante', help='Select student', required=True)
    student_id       = fields.Many2one('student.student', 'Estudiante', help='Select student', required=True)
    student_code     = fields.Char('Código', related='student_id.student_code', help='Enter student code', readonly=True)
    standard_id      = fields.Many2one('school.standard', 'Sección', help='Select student standard', required=True, tracking=True)
    school_id        = fields.Many2one('school.campus', 'Campus', help='Select Campus', required=True, tracking=True)
    subject_id       = fields.Many2one('subject.subject', 'Curso', related='standard_id.subject_id', required=True, help='Curso')
    inscription_date = fields.Date(string="Fecha", required=True, default=fields.Date.today)
    move_id          = fields.Many2one("account.move", "Factura Asociada", required=True, help="Link to the automatically generated Journal Items.")
    partner_id       = fields.Many2one("res.partner",'Partner', related='move_id.partner_id', help='Enter student code', readonly=True)
    student_partner_id = fields.Many2one("res.partner",'Student Partner', related='student_id.user_id.partner_id', help='Enter student code', readonly=True)

    company_id       = fields.Many2one('res.company', 'Companía', related='standard_id.company_id', store=True, help='Company_id of the school')
    photo            = fields.Image('Foto', related='student_id.photo', help='Attach student photo')

    move_type = fields.Selection(
         selection=[
             ('entry', 'Journal Entry'),
             ('out_invoice', 'Customer Invoice'),
             ('out_refund', 'Customer Credit Note'),
             ('in_invoice', 'Vendor Bill'),
             ('in_refund', 'Vendor Credit Note'),
             ('out_receipt', 'Sales Receipt'),
             ('in_receipt', 'Purchase Receipt'),
         ],
         string='Type',
         related='move_id.move_type',
         required=True,
         readonly=True,
         change_default=True,
         index=True,
         default="entry",
    )

    payment_state = fields.Selection(
        selection=PAYMENT_STATE_SELECTION,
        string="Status Pago",
        related='move_id.payment_state',
        store=True, 
        readonly=True,
        copy=False,
        tracking=True,
    )

    state_invoice = fields.Selection(
         selection=[
             ('draft', 'Draft'),
             ('posted', 'Posted'),
             ('cancel', 'Cancelled'),
         ],
         string='Status',
         related='move_id.state',
         required=True,
         readonly=True,
         copy=False,
         default='draft',
    )      
 
    eva_o = fields.Float('Evaluación Oral', help='Escriba la evaluación Oral', default=0)
    eva_e = fields.Float('Evaluación Escrita', help='Escriba la evaluación Escrita', default=0)
    eva_t = fields.Float('Promedio', readonly=True, help='Evaluación Promedio', default=0)
    
    nota  = fields.Float('Calificación', readonly=True, help='Evaluación Promedio', default=0)

    state            = fields.Selection([('draft', 'Draft'), 
                                         ('done', 'Done'),
                                         ('terminate', 'Terminate'), 
                                         ('cancel', 'Cancel'),
                                        ], 'Status', readonly=True, default="draft", help='State of the student registration form')
    
    state_aux        = fields.Selection([('preinscrito', 'Preinscrito'), 
                                         ('inscrito', 'Inscrito'),
                                         ('culminado', 'Culminado'), 
                                         ('retirado', 'Retirado'),
                                        ], 'Status', readonly=True, default="por iniciar", help='State of the student registration form'
                                        , compute="_compute_state")
    
    state_eva       = fields.Selection([('borrador', 'Borrador'), 
                                        ('aprobado', 'Aprobado'),
                                        ('aplazado', 'Aplazado'), 
                                        ('inasistente', 'Inasistente'),
                                       ], 'Valoración', readonly=True, default="borrador", help='State of the student registration form')
    
    note = fields.Text('Observaciones', help='Observaciones', states={'terminate,cancel': [('readonly', True)]})

    state_sec        = fields.Selection([('por iniciar', 'Por iniciar'), 
                                         ('iniciado', 'Iniciado'),
                                         ('culminado', 'Culminado'), 
                                        ], 'Status', readonly=True, default="por iniciar", tracking=True, help='State of the student registration form',
                                        related='standard_id.state_aux'
                                        )
    start_date      = fields.Date('Fecha de inicio', related='standard_id.start_date', help='Inicio del Lapso Académico')
    end_date        = fields.Date('Fecha de finalización', related='standard_id.end_date', help='End date of Lapso Académico')

    solvencia_state = fields.Selection(
        selection=SOLVENCIA_STATE_SELECTION,
        string="Status Solvencia",
        store=True, readonly=True,
        tracking=True,
        default='solvente'
    )

    def set_to_draft(self):
        '''Method to change state to draft'''
        self.state = 'draft'

    def set_done(self):
        '''Method to change state to done'''
        self.state = 'done'

    def admission_draft(self):
        '''Set the state to draft'''
        self.state = 'draft'

    def set_terminate(self):
        '''Set the state to terminate'''
        self.state = 'terminate'

    def cancel_admission(self):
        '''Set the state to cancel.'''
        self.state = 'cancel'

    def admission_done(self):
        '''Method to confirm admission'''
        self.state = 'done'
       #-------------------------------------------------------#
       #  GENERA LA ASISTENCIA , EVA SI LA SECCIÓN INIO        #
       #-------------------------------------------------------#
        if self.standard_id.state == 'done':
           self.generar_asi()
           self.generar_eva()
       #-------------------------------------------------------#
       #  ASIGNA LA SECCION EL REGISTRO DEL ESTUDIANTE         #
       #-------------------------------------------------------#
        self.student_id.state ='done'
        self.student_id.standard_id    = self.standard_id
        self.student_id.user_id.partner_id.is_student = True
        self.student_id.admission_date = self.inscription_date
       #-------------------------------------------------------#
       #  ASIGANA EL RI A LA FACTURA                           #
       #-------------------------------------------------------#
        self.move_id.inscripcion_id = self.id
        self.move_id.is_inscripcion = True
        self.standard_id._compute_total_student()

#-----------------------------------------------------------------------#
    def get_estado(self , sta):
        '''Method to compute la escala minima.'''

        if sta == 'draft':
           return 'preinscrito'
        elif sta == 'done':
           return 'inscrito' 
        elif sta == 'terminate':
           return 'culminado'
        elif sta == 'cancel':
           return 'retirado'
        else:
            return sta
        
        return sta           
#-----------------------------------------------------------------------#

    @api.model
    def create(self, vals):
         if vals.get('name', _('New')) == _('New'):
             vals['name'] = self.env['ir.sequence'].next_by_code('inscripcion.code') or _('New')
         res = super(StudentInscripcion, self).create(vals)
         return res

#------------------------------------------------------------------------------------------#
#  DEBERA LOS REGISTRO DE ASISTENCIAS A LOS STUDENT INSCRITOS UNA VEZ INICIADA LA SECCION  #
#------------------------------------------------------------------------------------------#
    def generar_asi(self):
         for record in self:
             
             domain         = [('standard_id', '=' , record.standard_id.id)]
             asistenciaObj  = self.env["subject.asistencia"].search(domain)
             asistenciasObj = self.env['subject.asistencias']

             if asistenciaObj:
                #----------------------------------------------------------------------------#
                #  CICLO DE LAS EVALUACIONES DE LA SECCION                                   #
                #----------------------------------------------------------------------------#
                for eva in asistenciaObj:
                    #raise ValidationError("Encontro las asistencia de la seccion: ..!" + "Nombre:" + str(eva.encuentro_id.name) + str(eva.state))

                    #----------------------------------------------------------------------------#
                    #  GENERA REGISTRO DE EVALUACION SI EL STATE ES DIFERENTE DE DRAFT           #
                    #----------------------------------------------------------------------------#
                    if eva.state in ['done','terminate']:
                       #raise ValidationError("Encontro las asistencia de la seccion: ..!" + "Nombre:" + str(eva.name) + "State:" + str(eva.state))

                       asistenciasObj.create({
                           
                                                'inscripcion_id': self.id,
                                                'asistencia_id' : eva.id,
                                                'student_id'    : self.student_id.id,
                                                'is_attended'   : False,
                                                'note'          : " ",
                            
                                            })

#------------------------------------------------------------------------------------------#
#  DEBERA LOS REGISTRO DE EVALUACIONES A LOS STUDENT INSCRITOS UNA VEZ INICIADA LA SECCION #
#------------------------------------------------------------------------------------------#
    
    def generar_eva(self):
         for record in self:
             
             domain          = [('standard_id', '=' , record.standard_id.id)]
             evaluacionObj   = self.env["standard.evaluacion"].search(domain)
             evaluacionesObj = self.env['standard.evaluaciones']
             actividadesObj  = self.env['standard.actividades']
             stu_id          = self.student_id.id
             stu_state       = self.student_id.state
             stu_nombre      = self.student_id.student_name
             ri_id           = self.id

             if evaluacionObj:
                #----------------------------------------------------------------------------#
                #  CICLO DE LAS EVALUACIONES DE LA SECCION                                   #
                #----------------------------------------------------------------------------#
                for eva in evaluacionObj:
                    #----------------------------------------------------------------------------#
                    #  GENERA REGISTRO DE EVALUACION SI EL STATE ES DIFERENTE DE DRAFT           #
                    #----------------------------------------------------------------------------#
                    if eva.state in ['done','terminate']:
                        evalua_id = evaluacionesObj.create({
                                                            
                                                            'inscripcion_id': ri_id,
                                                            'evaluacion_id' : eva.id,
                                                            'student_id'    : stu_id,
                                                            'nota'          : 0,
                                                                
                                                            })

                        no_act = len(eva.libroevas_id.actividad_ids)
                        r      = 1

                        while r <= no_act:
                            if r==1:
                               evalua_id.is_act1 = True
                               evalua_id.actividad1_id = eva.libroevas_id.actividad_ids[r-1].id
                            elif r==2:
                               evalua_id.is_act2 = True
                               evalua_id.actividad2_id = eva.libroevas_id.actividad_ids[r-1].id
                            elif r==3:
                               evalua_id.is_act3 = True
                               evalua_id.actividad3_id = eva.libroevas_id.actividad_ids[r-1].id
                            elif r==4:
                               evalua_id.is_act4 = True
                               evalua_id.actividad4_id = eva.libroevas_id.actividad_ids[r-1].id
                            elif r==5:
                               evalua_id.is_act5 = True
                               evalua_id.actividad5_id = eva.libroevas_id.actividad_ids[r-1].id
                            elif r==6:
                               evalua_id.is_act6 = True
                               evalua_id.actividad6_id = eva.libroevas_id.actividad_ids[r-1].id

                            r +=1

                        if no_act != 0:

                            j = 1
                            while j <= no_act:
                                    
                                act_id   = eva.libroevas_id.actividad_ids[j-1].id
                                act_name = eva.libroevas_id.actividad_ids[j-1].nombre

                                #-----------------------------------------------------------------------#
                                # GENERA EL REGISTRO A LOS STUDENT DONE                                  #
                                #-----------------------------------------------------------------------#

                                #raise ValidationError("Status: " + "estudiante ; " + stu_nombre + " Status: " + stu_state)
                               
                                actividadesObj.create({
                                                        'evaluacion_id' : evalua_id.id,
                                                        'actividad_id'  : act_id,
                                                        'student_id'    : stu_id,
                                                       })
                                j = j + 1

                    #raise ValidationError("Encontro las evaluaciones de la seccion: ..!" + "Nombre:" + str(eva.evaluacion_id.name) + "State:" + str(eva.state))

#-----------------------------------------------------------------------#    
    # def name_get(self):
    #     '''Method to display standard and division'''
    #     return [(rec.id, rec.name + '/' + rec.standard_id.code + '/' + rec.subject_id.code ) for rec in self]



      