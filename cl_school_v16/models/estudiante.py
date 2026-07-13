# See LICENSE file for full copyright and licensing details.

import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.modules import get_module_resource

from . import school

# from lxml import etree
# added import statement in try-except because when server runs on
# windows operating system issue arise because this library is not in Windows.
try:
    from odoo.tools import image_colorize
except:
    image_colorize = False


class SchoolStudent(models.Model):
    '''Defining a student information.'''

    _name = 'school.student'
    _description = 'Student Information'
    #_rec_name = 'rec'
    _order = 'student_ci'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('date_of_birth')
    def _compute_student_age(self):
        '''Method to calculate student age'''
        current_dt = fields.Date.today()
        for rec in self:
            rec.age = 0
            if rec.date_of_birth and rec.date_of_birth < current_dt:
                start = rec.date_of_birth
                age_calc = ((current_dt - start).days / 365)
                # Age should be greater than 0
                if age_calc > 0.0:
                    rec.age = age_calc

    @api.model
    def _default_image(self):
        '''Method to get default Image'''
        image_path = get_module_resource('hr', 'static/src/img',
                                         'default_image.png')
        return base64.b64encode(open(image_path, 'rb').read())

    user_id = fields.Many2one('res.users', 'User ID', ondelete="cascade", required=True, delegate=True, help='Select related user of the student')
   #-----------------------------------------------------------------------#
   # SE AGREGO ESTE CAMPO PARA LA RELACION CON RES.PARTNER                 #
   #-----------------------------------------------------------------------#
 
    school_id = fields.Many2one('school.campus', 'Campus', states={'done': [('readonly', True)]}, help='Select school', tracking=True)
    student_name = fields.Char('Student Nombre', related='user_id.name', store=True, readonly=True, help='Student Nombre')

    pid = fields.Char('Estudiante ID', required=True, default=lambda self: _('New'), help='Personal IDentification Number')
    reg_code = fields.Char('Registration Code', help='Student Registration Code')
   #-----------------------------------------------------------------------#
   # SE AGREGO ESTE CAMPO                                                  #
   #-----------------------------------------------------------------------#
    student_ci = fields.Char('Student CI', help='Enter student ci')
   #-----------------------------------------------------------------------#
    student_code = fields.Char('Student Code', help='Enter student code')
    admission_date = fields.Date('Fecha de Inscripción', default=fields.Date.today(), help='Enter student admission date')
    photo = fields.Binary('Photo', default=_default_image, help='Attach student photo')
    date_of_birth = fields.Date('BirthDate', states={'done': [('readonly', True)]}, help='Enter student date of birth')
    age = fields.Integer(compute='_compute_student_age', string='Age', readonly=True, help='Enter student age')
    roll_no = fields.Integer('No.', readonly=True, help='Enter student roll no.')
    contact_phone = fields.Char('Phone no.', help='Enter student phone no.')
    contact_mobile = fields.Char('Mobile no', help='Enter student mobile no.')
    last = fields.Char('Surname', states={'done': [('readonly', True)]}, help='Enter student last name')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Sexo', states={'done': [('readonly', True)]}, help='Select student gender')
    active = fields.Boolean(default=True, help='Activate/Deactivate student record', tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'),
        ('terminate', 'Terminate'), ('cancel', 'Cancel'),
        ('alumni', 'Alumni')], 'Status', readonly=True, default="draft", tracking=True, help='State of the student registration form')
    
    @api.model
    def create(self, vals):
        
        '''Method to create user when student is created'''
        if vals.get('pid', _('New')) == _('New'):
            vals['pid'] = self.env['ir.sequence'
                                   ].next_by_code('student.student'
                                                  ) or _('New')
            
        if vals.get('pid', False):
            vals['login'] = vals['pid']
            vals['password'] = vals['pid']
        else:
            raise UserError(_(
                    "Error! PID not valid so record will not be saved."))
        
        if vals.get('company_id', False):
            company_vals = {'company_ids': [(4, vals.get('company_id'))]}
            vals.update(company_vals)
        

        if vals.get('email'):
            school.emailvalidation(vals.get('email'))
    
        res = super(SchoolStudent, self).create(vals)
        
        #raise UserError(_("Warning! En create, despues del eMAIL ..!"))

        emp_grp = self.env.ref('base.group_user')

        done_student = self.env.ref('school.group_school_student')
        group_list = [done_student.id, emp_grp.id]
        res.user_id.write({'groups_id': [(6, 0, group_list)]})
        
        # if res.state == 'draft':
        #     admission_group = self.env.ref('school.group_is_admission')
        #     new_grp_list = [admission_group.id, emp_grp.id]
        #     res.user_id.write({'groups_id': [(6, 0, new_grp_list)]})
        # elif res.state == 'done':
        #     done_student = self.env.ref('school.group_school_student')
        #     group_list = [done_student.id, emp_grp.id]
        #     res.user_id.write({'groups_id': [(6, 0, group_list)]})

        #raise UserError(_("Warning! En create, despues al final ..!"))

        return res
    
   #-----------------------------------------------------------------------#
   # SE AGREGO ESTE METODO                                                 #
   #-----------------------------------------------------------------------#
    @api.constrains('student_ci')
    def check_student_ci(self):
        '''Method to check student should be unique'''        

        domain = [('student_ci', '=', self.student_ci)]
        
        if self.id.origin:
               domain.append(('id', '!=', self.id.origin))
   
        if self.env['school.student'].search(domain, limit=1):
               aux_ci = self.student_ci
               
               raise ValidationError(_("The identification of student should be unique: " + aux_ci))        
   #-----------------------------------------------------------------------#
    
    def set_to_draft(self):
        '''Method to change state to draft'''
        self.state = 'draft'

    def set_alumni(self):
        '''Method to change state to alumni'''
        for rec in self:
            rec.state = 'alumni'
            #rec.standard_id._compute_total_student()
            rec.active = False
            rec.user_id.active = False

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
        school_standard_obj = self.env['school.standard']
        ir_sequence = self.env['ir.sequence']
        student_group = self.env.ref('school.group_school_student')
        emp_group = self.env.ref('base.group_user')
        for rec in self:
            if not rec.standard_id:
                raise ValidationError(_("Please select class!"))
            if rec.standard_id.remaining_seats <= 0:
                raise ValidationError(_('Seats of class %s are full'
                                        ) % rec.standard_id.standard_id.name)
            domain = [('school_id', '=', rec.school_id.id)]
            # Checks the standard if not defined raise error
            if not school_standard_obj.search(domain):
                raise UserError(_(
                        "Warning! The standard is not defined in school!"))
            # Assign group to student
            rec.user_id.write({'groups_id': [(6, 0,
                                [emp_group.id, student_group.id])]})
            # Assign roll no to student
            number = 1
            for rec_std in rec.search(domain):
                rec_std.roll_no = number
                number += 1
            # Assign registration code to student
            reg_code = ir_sequence.next_by_code('student.registration')
            registation_code = (str(rec.school_id.state_id.name) + str('/') +
                                str(rec.school_id.city) + str('/') +
                                str(rec.school_id.name) + str('/') +
                                str(reg_code))
            stu_code = ir_sequence.next_by_code('student.code')
            student_code = (str(rec.school_id.code) + str('/') +
                            str(rec.year.code) + str('/') +
                            str(stu_code))
            rec.write({'state': 'done',
                       'admission_date': fields.Date.today(),
                       'student_code': student_code,
                       'reg_code': registation_code})
            template = self.env['mail.template'].sudo().search([('name', 'ilike', 'Admission Confirmation')], limit=1)
            if template:
                for user in rec.parent_id:
                    subject = _("About Admission Confirmation")
                    if user.email:
                        body = """
                        <div>
                            <p>Dear """ + str(user.display_name) + """,
                            <br/><br/>
                            Admission of """+str(rec.display_name)+""" has been confirmed in """+str(rec.school_id.name)+""".
                            <br></br>
                            Thank You.
                        </div>
                        """
                        template.send_mail(rec.id, email_values={
                            'email_from': self.env.user.email or '',
                            'email_to': user.email,
                            'subject': subject,
                            'body_html': body,
                            }, force_send=True)
        return True
