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

class SchoolCurso(models.Model):
    '''Defining a standard related to school.'''

    _name = 'school.curso'
    _description = 'School Standards / SECCIONES'
 
    _order = "school_id, code"


    name = fields.Char(string='Curso Nro.', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    code = fields.Char('Código', required=True, help='Código de la sección')
    school_id = fields.Many2one('school.school', 'Sede', required=True, help='School of the following standard')
    subject_id = fields.Many2one('school.subject', 'Cursos/Asignaturas', required=True, help='School of the following standard')
    standard_id = fields.Many2one('standard.standard', 'Nivel', required=True, help='Standard')
    division_id = fields.Many2one('standard.division', 'Turno', required=True, help='Standard division')
    medium_id = fields.Many2one('standard.medium', 'Modalidad', required=True, help='Medium of the standard')
    user_id = fields.Many2one('school.teacher', 'Profesor', help='Teacher of the standard')
    
    student_ids = fields.One2many('student.inscripcion', 'standard_id', 'Student In Class', compute='_compute_student', store=True, help='Students which are in this standard')
    color = fields.Integer('Color Index', help='Index of color')
    cmp_id = fields.Many2one('res.company', 'Company Nombre', related='school_id.company_id', store=True, help='Company_id of the school')
    
    capacity = fields.Integer("Capacidad", help='Standard capacity')
    
    class_room_id = fields.Many2one('class.room', 'Salón de Clases', help='Class room of the standard')
    description = fields.Text('Horario de Clases', help='Horario')

    state = fields.Selection([('draft', 'Draft'), 
                              ('done', 'Done'),
                              ('terminate', 'Terminate'), 
                              ('cancel', 'Cancel')], 'Status', readonly=True, default="draft", help='State of the student registration form')
    
    def set_draft(self):
        '''Method to change state to draft'''
        self.state = 'draft'

    def set_done(self):
        '''Method to change state to done'''
        self.state = 'done'

    def set_terminate(self):
        '''Set the state to terminate'''
        self.state = 'terminate'

    def set_cancel(self):
        '''Set the state to cancel.'''
        self.state = 'cancel'
    
    @api.model
    def create(self, vals):
         if vals.get('name', _('New')) == _('New'):
             vals['name'] = self.env['ir.sequence'].next_by_code('curso.code') or _('New')
         res = super(SchoolCurso, self).create(vals)
         return res
   
    
