# See LICENSE file for full copyright and licensing details.



from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.translate import _


class StudentRetiro(models.Model):
    '''Defining a student Retiro.'''

    _name = 'student.retiro'
    _description = 'Student Retiro'
    _order = "retiro_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']
 
    # @api.constrains('student_id')
    # def _check_code(self):
    #      for record in self:
    #          domain = [('id', '!=', record.id), ('student_id', '=' , record.student_id.id), ('standard_id', '=' , record.standard_id.id)]
    #          if self.env["student.inscripcion"].search(domain):
    #             raise ValidationError("Error: El estudiante ya està inscrito en la SECCIÒN..!")
    
    @api.constrains('standard_id')
    def _check_cupo(self):
         for record in self:
            if self.standard_id.remaining_seats<=0:
                raise ValidationError("Error: La sección no tiene cupos disponibles..!")           
    
    # @api.depends('state')
    # def _compute_state(self):
    #     '''Method to compute total student.'''
    #     for rec in self:
    #         rec.state_aux = self.get_estado(rec.state)

    name             = fields.Char(string='RI Nro.', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    student_id       = fields.Many2one('student.student', 'Estudiante', help='Select student', required=True)
    student_code     = fields.Char('Código', related='student_id.student_code', help='Enter student code', readonly=True)
    ri_id            = fields.Many2one('student.inscripcion', 'RI', help='Select student', required=True, states={'terminate': [('readonly', True)]})
    tiporetiro_id    = fields.Many2one('school.tiporetiro', 'Tipo', help='Selecione el tipo de retiro', required=True, states={'terminate': [('readonly', True)]})

    standard_id      = fields.Many2one('school.standard', 'Sección', related='ri_id.standard_id', help='Select student standard', required=True, tracking=True)
    school_id        = fields.Many2one('school.campus', 'Campus', related='ri_id.school_id', help='Select Campus', required=True, tracking=True)
    subject_id       = fields.Many2one('subject.subject', 'Curso', related='standard_id.subject_id', required=True, help='Curso')
    retiro_date      = fields.Date(string="Fecha", required=True, default=fields.Date.today)
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
    
    #name = fields.Char(string='RI Nro.', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    
    note = fields.Text('Observaciones', states={'terminate': [('readonly', True)]}, help='Observaciones')

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
        self.state = 'terminate'
        self.ri_id.state ='cancel'
        self.ri_id.state_aux ='retirado'
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
             vals['name'] = self.env['ir.sequence'].next_by_code('retiro.code') or _('New')
         res = super(StudentRetiro, self).create(vals)
         return res

#------------------------------------------------------------------------------------------#
#  DEBERA LOS REGISTRO DE ASISTENCIAS A LOS STUDENT INSCRITOS UNA VEZ INICIADA LA SECCION  #
#------------------------------------------------------------------------------------------#
 


      