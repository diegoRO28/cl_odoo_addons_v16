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

class StudentCambio(models.Model):
    '''Defining a student Cabio de Seccion.'''

    _name        = 'student.cambio'
    _description = 'Student Cambio/Seccion'
    _order       = "cambio_date desc"

    _inherit     = ['mail.thread', 'mail.activity.mixin']

#-----------------------------------------------------------------------#
    @api.constrains('standard_id')
    def _check_cupo(self):
         for record in self:
            if self.standard_id.remaining_seats<=0:
                raise ValidationError("Error: La sección no tiene cupos disponibles..!")     
            
#-----------------------------------------------------------------------#
    @api.constrains('standard_des_id')
    def _check_sec_des(self):
         for record in self:
            if self.standard_id == self.standard_des_id:
                raise ValidationError("Error: La sección ORIGEN y DESTINO las mismas. Deben ser diferenctes..!")
                  
#-----------------------------------------------------------------------#
    name             = fields.Char(string='RC Nro.', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    student_id       = fields.Many2one('student.student', 'Estudiante', help='Select student', required=True)
    student_code     = fields.Char('Código', related='student_id.student_code', help='Enter student code', readonly=True)
    ri_id            = fields.Many2one('student.inscripcion', 'RI', help='Select student', required=True, states={'terminate': [('readonly', True)]})
    tipocambio_id    = fields.Many2one('school.tipocambio', 'Tipo', help='Selecione el tipo de cambio', required=True, states={'terminate': [('readonly', True)]})

    standard_id      = fields.Many2one('school.standard', 'Sección', related='ri_id.standard_id', help='Select student standard')
    school_id        = fields.Many2one('school.campus', 'Campus', related='ri_id.school_id', help='Select Campus', required=True, tracking=True)
    subject_id       = fields.Many2one('subject.subject', 'Curso', related='standard_id.subject_id', required=True, help='Curso')
    cambio_date      = fields.Date(string="Fecha", required=True, default=fields.Date.today)
    inscripcion_date = fields.Date(string="Fecha", related='ri_id.inscription_date')

    move_id          = fields.Many2one("account.move", "Factura Asociada", required=True, related='ri_id.move_id', help="Link to the automatically generated Journal Items.")
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

    # payment_state = fields.Selection(
    #     selection=PAYMENT_STATE_SELECTION,
    #     string="Status Pago",
    #     related='move_id.payment_state',
    #     store=True, 
    #     readonly=True,
    #     copy=False,
    #     tracking=True,
    # )

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
    
    state            = fields.Selection([('draft', 'Draft'), 
                                         ('done', 'Done'),
                                         ('terminate', 'Terminate'), 
                                         ('cancel', 'Cancel'),
                                        ], 'Registro Inscripciòn', readonly=True, default="draft", help='State of the student registration form')
    
    state_aux        = fields.Selection([('preinscrito', 'Preinscrito'), 
                                         ('inscrito', 'Inscrito'),
                                         ('culminado', 'Culminado'), 
                                         ('retirado', 'Retirado'),
                                        ], 'Status', readonly=True, default="por iniciar", help='State of the student registration form'
                                        , related='ri_id.state_aux')
    
    state_eva       = fields.Selection([('borrador', 'Borrador'), 
                                        ('aprobado', 'Aprobado'),
                                        ('aplazado', 'Aplazado'), 
                                        ('inasistente', 'Inasistente'),
                                       ], 'Valoración', readonly=True, default="borrador", help='State of the student registration form')
        
    note = fields.Text('Observaciones', states={'terminate': [('readonly', True)]}, help='Observaciones')
    
    school_des_id    = fields.Many2one('school.campus', 'Campus', help='Select Campus', required=True, tracking=True)
    standard_des_id  = fields.Many2one('school.standard', 'Sección', help='Select student standard', required=True, tracking=True)
    subject_des_id   = fields.Many2one('subject.subject', 'Curso', related='standard_des_id.subject_id', required=True, help='Curso')
    company_des_id   = fields.Many2one('res.company', 'Companía', related='standard_des_id.company_id', store=True, help='Company_id of the school')


#-----------------------------------------------------------------------#
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

#-----------------------------------------------------------------------#
    def genera_registro_inscripcion(self):
        '''Method to compute la escala minima.'''

        try:
            note        = 'CAMBIO DE SECCIÓN: VIENE DE LA SECCIÓN: ' + self.standard_id.code + "/" + self.standard_id.subject_id.nombre
            inscrip_obj = self.env['student.inscripcion']

            record_inscrip = inscrip_obj.create({
                                'inscription_date' : self.cambio_date,
                                'student_id'       : self.student_id.id,
                                'school_id'        : self.school_des_id.id,
                                'standard_id'      : self.standard_des_id.id,
                                'move_id'          : self.move_id.id,
                                'state'            : 'done',
                                'note'             : note
                               }) 
            record_inscrip.admission_done()
        
        except Exception as error:
            raise ValidationError(f'Error al generar el registro de inscripción: \n {error}')      
        
#-----------------------------------------------------------------------#
    def admission_done(self):
        '''Method to confirm admission'''

        #--------------------------------------------------------#
        #               DATOS DEL RETIRO (SECCION ORIGEN)        #
        #--------------------------------------------------------#
        self.state           = 'terminate'
        self.ri_id.state     ='cancel'
        self.ri_id.state_aux ='retirado'
        self.standard_id._compute_total_student()

        #----------------------------------------------------------#
        #               DATOS DE LA INSCRIPCION (SECCION DESTINO)  #
        #----------------------------------------------------------#

        self.genera_registro_inscripcion()

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
             vals['name'] = self.env['ir.sequence'].next_by_code('cambio.code') or _('New')
         res = super(StudentCambio, self).create(vals)
         return res