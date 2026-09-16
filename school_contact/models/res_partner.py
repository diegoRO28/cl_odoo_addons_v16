# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

#------------------------------------------------------------------------------------------------
# PARTNER
#------------------------------------------------------------------------------------------------

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    is_student   = fields.Boolean(string="Es Estudiante ?", default=False)
    
    student_id   = fields.Many2one('student.student', 'Estudiante', help='Select student')
    student_ci   = fields.Char('Identificaciòn', related='student_id.student_id.student_ci', help='Escriba la iIdentificaciòn del estudiante')
    student_code = fields.Char('Còdigo', related='student_id.student_id.student_code', help='Escriba el codigo del estudiante')
    standard_id  = fields.Many2one('school.standard', 'Sección',  related='student_id.student_id.standard_id', help='Select student standard', tracking=True)
    # name = fields.Char('Nombre', related='student_id.student_id.full_name', help='Escriba el nombre del estudiante')
   
    parent_name    = fields.Char('Nombre', related='student_id.student_id.parent_name', help='Escriba el codigo del estudiante' )
    parent_ci      = fields.Char('Identificación', related='student_id.student_id.parent_ci', help='Escriba ls identificación del representante' )
    parent_street  = fields.Char('Direcciòn', related='student_id.student_id.parent_street', help='Escriba el codigo del estudiante')
    parent_street2 = fields.Char('Direcciòn', related='student_id.student_id.parent_street2', help='Escriba el codigo del estudiante')
    parent_city    = fields.Char('Ciudad', related='student_id.student_id.parent_city', help='Escriba el codigo del estudiante')
    #parent_state_id = fields.Char('Estado', related='student_id.student_id.parent_state_id')

    parent_phone   = fields.Char('Telèfono', related='student_id.student_id.parent_phone', help='Escriba el codigo del estudiante')
    parent_mobile  = fields.Char('Mòvil', related='student_id.student_id.parent_mobile', help='Escriba el codigo del estudiante')
    parent_email   = fields.Char('eMail', related='student_id.student_id.parent_email', help='Escriba el codigo del estudiante')
  
    note       = fields.Char('Observaciones')

    

#------------------------------------------------------------------------------------------------
# ORDER
#------------------------------------------------------------------------------------------------

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    is_student   = fields.Boolean(string="Es Estudiante ?", default=False)
    
    student_id   = fields.Many2one('student.student', 'Estudiante', related='partner_id.student_id', help='Select student')
    student_ci   = fields.Char('Identificaciòn', related='student_id.student_id.student_ci', help='Escriba la iIdentificaciòn del estudiante')
    student_code = fields.Char('Còdigo', related='student_id.student_id.student_code', help='Escriba el codigo del estudiante')
    standard_id  = fields.Many2one('school.standard', 'Sección',  related='student_id.student_id.standard_id', help='Select student standard', tracking=True)

    parent_name    = fields.Char('Nombre', related='student_id.student_id.parent_name', help='Escriba el codigo del estudiante' )
    parent_ci      = fields.Char('Identificación', related='student_id.student_id.parent_ci', help='Escriba ls identificación del representante' )
    parent_street  = fields.Char('Direcciòn', related='student_id.student_id.parent_street', help='Escriba el codigo del estudiante')
    parent_street2 = fields.Char('Direcciòn', related='student_id.student_id.parent_street2', help='Escriba el codigo del estudiante')
    parent_city    = fields.Char('Ciudad', related='student_id.student_id.parent_city', help='Escriba el codigo del estudiante')

    parent_phone   = fields.Char('Telèfono', related='student_id.student_id.parent_phone', help='Escriba el codigo del estudiante')
    parent_mobile  = fields.Char('Mòvil', related='student_id.student_id.parent_mobile', help='Escriba el codigo del estudiante')
    parent_email   = fields.Char('eMail', related='student_id.student_id.parent_email', help='Escriba el codigo del estudiante')

#------------------------------------------------------------------------------------------------
# ACCOUNT MOVE
#------------------------------------------------------------------------------------------------

class account_move(models.Model):
    _inherit = 'account.move'
    
    is_student   = fields.Boolean(string="Es Estudiante ?", default=False)
    
    student_id   = fields.Many2one('student.student', 'Estudiante', related='partner_id.student_id', help='Select student')
    student_ci   = fields.Char('Identificaciòn', related='student_id.student_id.student_ci', help='Escriba la iIdentificaciòn del estudiante')
    student_code = fields.Char('Còdigo', related='student_id.student_id.student_code', help='Escriba el codigo del estudiante')
    standard_id  = fields.Many2one('school.standard', 'Sección',  related='student_id.student_id.standard_id', help='Select student standard', tracking=True)

    parent_name    = fields.Char('Nombre', related='student_id.student_id.parent_name', help='Escriba el codigo del estudiante' )
    parent_ci      = fields.Char('Identificación', related='student_id.student_id.parent_ci', help='Escriba ls identificación del representante' )
    parent_street  = fields.Char('Direcciòn', related='student_id.student_id.parent_street', help='Escriba el codigo del estudiante')
    parent_street2 = fields.Char('Direcciòn', related='student_id.student_id.parent_street2', help='Escriba el codigo del estudiante')
    parent_city    = fields.Char('Ciudad', related='student_id.student_id.parent_city', help='Escriba el codigo del estudiante')
 
    parent_phone   = fields.Char('Telèfono', related='student_id.student_id.parent_phone', help='Escriba el codigo del estudiante')
    parent_mobile  = fields.Char('Mòvil', related='student_id.student_id.parent_mobile', help='Escriba el codigo del estudiante')
    parent_email   = fields.Char('eMail', related='student_id.student_id.parent_email', help='Escriba el codigo del estudiante')

    #is_inscripcion = fields.Boolean(string="Es RI ?", default=False)
    #inscripcion_id = fields.Many2one('student.inscripcion', 'RI', help='Registro de Inscripción')

    inscripcion_id = fields.Many2one('student.inscripcion', 
                                     domain="[('move_id','=', id)]",
                                     store=True, 
                                     help='Students which are in this standard',
                                    )



#------------------------------------------------------------------------------------------------
# ACCOUNT PAYMENT
#------------------------------------------------------------------------------------------------
class account_payment(models.Model):
    _inherit = 'account.payment'
    
    student_id   = fields.Many2one('student.student', 'Estudiante', related='partner_id.student_id', help='Select student')
    student_ci   = fields.Char('Identificaciòn', related='student_id.student_id.student_ci', help='Escriba la iIdentificaciòn del estudiante')
    student_code = fields.Char('Còdigo', related='student_id.student_id.student_code', help='Escriba el codigo del estudiante')
