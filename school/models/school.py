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

def emailvalidation(email):
    """Check valid email."""
    if email:
        email_regex = re.compile(EM)
        if not email_regex.match(email):
            raise ValidationError(_("""This seems not to be valid email.
Please enter email in correct format!"""))


class AcademicYear(models.Model):
    '''Defines an Lapso Académico.'''

    _name = "academic.year"
    _description = "Lapso Académico"
    _order = "sequence"

    sequence = fields.Integer('Correlativo', required=True,
                              help="Correlativo order you want to see this year.")
    name = fields.Char('Nombre', required=True, help='Nombre del Lapso Académico')
    code = fields.Char('Código', required=True, help='Código del Lapso Académico')
    date_start = fields.Date('Fecha de inicio', required=True,
                             help='Starting date of Lapso Académico')
    date_stop = fields.Date('Fecha Fin', required=True,
                            help='Ending of Lapso Académico')
    month_ids = fields.One2many('academic.month', 'year_id', 'Meses',
                                help="Related Academic months")
    grade_id = fields.Many2one('grade.master', "Grade", help='Grade')
    current = fields.Boolean('Actual', help="Set Active Current Year")
    description = fields.Text('Descripción', help='Descripción')

    @api.model
    def next_year(self, sequence):
        '''This method assign sequence to years'''
        year_rec = self.search([('sequence', '>', sequence)], order='id',
                            limit=1)
        if year_rec:
            return year_rec.id or False

    def name_get(self):
        '''Method to display name and code'''
        return [(rec.id, ' [' + rec.code + ']' + rec.name) for rec in self]

    def generate_academicmonth(self):
        """Generate academic months."""
        interval = 1
        month_obj = self.env['academic.month']
        for rec in self:
            start_date = rec.date_start
            while start_date < rec.date_stop:
                end_date = start_date + relativedelta(months=interval, days=-1)
                if end_date > rec.date_stop:
                    end_date = rec.date_stop
                month_obj.create({
                    'name': start_date.strftime('%B'),
                    'code': start_date.strftime('%m/%Y'),
                    'date_start': start_date,
                    'date_stop': end_date,
                    'year_id': rec.id,
                })
                start_date = start_date + relativedelta(months=interval)

    @api.constrains('date_start', 'date_stop')
    def _check_academic_year(self):
        '''Method to check start date should be greater than end date
           also check that dates are not overlapped with existing academic
           year'''
        new_start_date = self.date_start
        new_stop_date = self.date_stop
        delta = new_stop_date - new_start_date
        if delta.days > 365 and not calendar.isleap(new_start_date.year):
            raise ValidationError(_(
                "The duration of the Lapso Académico is invalid."))
        if (self.date_stop and self.date_start and
                self.date_stop < self.date_start):
            raise ValidationError(_(
        "The start date of the Lapso Académico should be less than end date."))
        for old_ac in self.search([('id', 'not in', self.ids)]):
            # Check start date should be less than stop date
            if (old_ac.date_start <= self.date_start <= old_ac.date_stop or
                    old_ac.date_start <= self.date_stop <= old_ac.date_stop):
                raise ValidationError(_(
                    "Error! You cannot define overlapping academic years."))

    @api.constrains('current')
    def check_current_year(self):
        '''Constraint on active current year'''
        current_year_rec = self.search_count([('current', '=', True)])
        if current_year_rec >= 2:
            raise ValidationError(_(
                            "Error! You cannot set two current year active!"))


class AcademicMonth(models.Model):
    '''Defining a month of an Lapso Académico.'''

    _name = "academic.month"
    _description = "Academic Month"
    _order = "date_start"

    name = fields.Char('Nombre', required=True, help='Nombre')
    code = fields.Char('Código', required=True, help='Código')
    date_start = fields.Date('Inicio del Lapso', required=True,
                             help='Start date')
    date_stop = fields.Date('Fin del Lapso', required=True,
                            help='End Date')
    year_id = fields.Many2one('academic.year', 'Lapso Académico', required=True,
                              help="Related Lapso Académico ")
    description = fields.Text('Descripción', help='Descripción')

    _sql_constraints = [
        ('month_unique', 'unique(date_start, date_stop, year_id)',
         'Academic Month should be unique!'),
    ]

    @api.constrains('year_id', 'date_start', 'date_stop')
    def _check_year_limit(self):
        '''Method to check year limit'''
        if self.year_id and self.date_start and self.date_stop:
            if (self.year_id.date_stop < self.date_stop or
                    self.year_id.date_stop < self.date_start or
                    self.year_id.date_start > self.date_start or
                    self.year_id.date_start > self.date_stop):
                raise ValidationError(_(
        "Some of the months periods overlap or is not in the Lapso Académico!"))

    @api.constrains('date_start', 'date_stop')
    def check_months(self):
        '''Method to check duration of date'''
        if (self.date_stop and self.date_start and
                self.date_stop < self.date_start):
            raise ValidationError(_(
        "Fin del Lapso date should be greater than Inicio del Lapsos Date!"))
        """Check start date should be less than stop date."""
        exist_month_rec = self.search([('id', 'not in', self.ids)])
        for old_month in exist_month_rec:
            if old_month.date_start <= \
                    self.date_start <= old_month.date_stop \
                    or old_month.date_start <= \
                    self.date_stop <= old_month.date_stop:
                raise ValidationError(_(
                            "Error! You cannot define overlapping months!"))


class StandardMedium(models.Model):
    ''' Defining a medium(ENGLISH, HINDI, GUJARATI) related to standard'''

    _name = "standard.medium"
    _description = "Standard Medium"
    _order = "code"

    sequence = fields.Integer('Correlativo', help='Correlativo of the record')
    name = fields.Char('Nombre', required=True,
                       help='Medium of the standard')
    code = fields.Char('Código', required=True,
                       help='Medium code')
    description = fields.Text('Descripción', help='Descripción')


class StandardDivision(models.Model):
    '''Defining a division(A, B, C) related to standard'''

    _name = "standard.division"
    _description = "Standard Division"
    _order       = "name"
    _rec_name    = "name"

    # sequence = fields.Integer('Correlativo', required=True,
    #                           help='Correlativo of the record')
    name = fields.Char('Nombre', required=True,
                       help='Division of the standard')
    code = fields.Char('Código', required=True,
                       help='Standard code')
    description = fields.Text('Descripción', help='Descripción')


class StandardStandard(models.Model):
    '''Defining Standard Information.'''

    _name = 'standard.standard'
    _description = 'Standard Information'
    _order = "sequence"

    sequence = fields.Integer('Correlativo', help='Correlativo of the record')
    name = fields.Char('Nombre', required=True,
                       help='Standard name')
    code = fields.Char('Código', required=True,
                       help='Código of standard')
    description = fields.Text('Descripción', help='Descripción')

    @api.model
    def next_standard(self, sequence):
        '''This method check sequence of standard'''
        stand_rec = self.search([('sequence', '>', sequence)], order='id',
                                limit=1)
        return stand_rec and stand_rec.id or False


# class SchoolStandard(models.Model):
#     '''Defining a standard related to school.'''

#     _name = 'school.standard'
#     _description = 'School Standards / SECCIONES'
#     _rec_name = "standard_id"
#     _order = "school_id, code"

#     @api.depends('standard_id', 'school_id', 'division_id', 'medium_id',
#                  'school_id')
#     def _compute_student(self):
#         '''Compute student of done state'''
#         student_obj = self.env['student.student']
#         for rec in self:
#             rec.student_ids = student_obj.\
#                 search([('standard_id', '=', rec.id),
#                         ('school_id', '=', rec.school_id.id),
#                         ('division_id', '=', rec.division_id.id),
#                         ('medium_id', '=', rec.medium_id.id),
#                         ('state', '=', 'done')])

#     @api.depends('subject_ids')
#     def _compute_subject(self):
#         '''Method to compute subjects.'''
#         for rec in self:
#             rec.total_no_subjects = len(rec.subject_ids)

#     @api.depends('student_ids')
#     def _compute_total_student(self):
#         '''Method to compute total student.'''
#         for rec in self:
#             rec.total_students = len(rec.student_ids)

#     @api.depends("capacity", "total_students")
#     def _compute_remain_seats(self):
#         '''Method to compute remaining seats.'''
#         for rec in self:
#             rec.remaining_seats = rec.capacity - rec.total_students
#    #-----------------------------------------------------------------------#
#    # SE AGREGO ESTE CAMPO                                                  #
#    #-----------------------------------------------------------------------#
#     code = fields.Char('Código', required=True, help='Código de la sección')
#    #-----------------------------------------------------------------------#
#     school_id = fields.Many2one('school.school', 'Sede', required=True,
#                                 help='School of the following standard')
#     standard_id = fields.Many2one('standard.standard', 'Nivel',
#                                   required=True, help='Standard')
#     division_id = fields.Many2one('standard.division', 'Turno',
#                                   required=True, help='Standard division')
#     medium_id = fields.Many2one('standard.medium', 'Modalidad', required=True,
#                                 help='Medium of the standard')
#     subject_id = fields.Many2one('subject.subject', 'Curso', required=True, help='Curso')

#     subject_ids = fields.Many2many('subject.subject', 'subject_standards_rel',
#                                    'subject_id', 'standard_id', 'Subject',
#                                    help='Subjects of the standard')
#     user_id = fields.Many2one('school.teacher', 'Profesor',required=True, help='Teacher of the standard')
#     # student_ids = fields.One2many('student.student', 'standard_id',
#     #                               'Student In Class',
#     #                               compute='_compute_student', store=True,
#     #                               help='Students which are in this standard'
#     #                               )

#     student_ids = fields.One2many('student.inscripcion', 'standard_id',
#                                   'Student In Class',
#                                   compute='_compute_student', store=True,
#                                   help='Students which are in this standard'
#                                   )
#     color = fields.Integer('Color Index', help='Index of color')
#     cmp_id = fields.Many2one('res.company', 'Company Nombre',
#                              related='school_id.company_id', store=True,
#                              help='Company_id of the school')
#     # syllabus_ids = fields.One2many('subject.syllabus', 'standard_id',
#     #                                'Syllabus',
#     #                                help='Syllabus of the following standard')
#     total_no_subjects = fields.Integer('Total No of Subject',
#                                        compute="_compute_subject",
#                                        help='Total subjects in the standard')
#     name = fields.Char('Nombre', help='Standard name')
#     capacity = fields.Integer("Capacidad", help='Standard capacity')
#     total_students = fields.Integer("Total Inscritos",
#                                     compute="_compute_total_student",
#                                     store=True,
#                                     help='Total students of the standard')
#     remaining_seats = fields.Integer("Cupos Disponibles",
#                                      compute="_compute_remain_seats",
#                                      store=True,
#                                      help='Remaining seats of the standard')
#     class_room_id = fields.Many2one('class.room', 'Salón de Clases', required=True, help='Class room of the standard')
#    #-----------------------------------------------------------------------#
#    # DESARROLLO PROPIO: SE AGREGO ESTE CAMPO Y SUS ESTADOS                 #
#    #-----------------------------------------------------------------------#  
#     description = fields.Text('Horario de Clases', help='Horario')

#     state = fields.Selection([('draft', 'Draft'), ('done', 'Done'),
#         ('terminate', 'Terminate'), ('cancel', 'Cancel')], 'Status', readonly=True, default="draft",
#         tracking=True, help='State of the student registration form')
    
#     def set_draft(self):
#         '''Method to change state to draft'''
#         self.state = 'draft'

#     def set_done(self):
#         '''Method to change state to done'''
        
#         no_subjects = self.get_no_subjects()
#         #raise ValidationError(_( "Error : No subjects: " + str(no_subjects) ))
#         if no_subjects!=0:
#              self.state = 'done'
#              self.generate_encuentros(no_subjects)
#              self.generate_evaluaciones(no_subjects)

#         else:
#              raise ValidationError(_( "Error : No hay Asignaturas en el curso" ))

#     def set_terminate(self):
#         '''Set the state to terminate'''
#         self.state = 'terminate'

#     def set_cancel(self):
#         '''Set the state to cancel.'''
#         self.state = 'cancel'

#    #-----------------------------------------------------------------------#
#    # DESARROLLO PROPIO: SE AGREGO ESTE METODO                              #
#    #-----------------------------------------------------------------------#  
#     @api.onchange('code')
#     def _onchange_code(self):
#         if not self.code:
#             return
        
#         self.code = self.code.upper()

#         digito = self.code.isalnum()
#         if not digito:
#             aux = self.code
            
#             return {'warning': {
#                 'title': ("Mensaje de Error:"), 
#                 'message': ("Error: El código de la sección debe contener sólo valores alfanumérico..! "), 
#             }}
        
#         if len(self.code) > 3:
#             aux = self.code
            
#             return {'warning': {
#                 'title': ("Mensaje de Error:"), 
#                 'message': ("Error: El còdigo de la secciòn debe contener hasta 3 caracteres..! "),  
#             }}
#     #-----------------------------------------------------------------------#    
#     def get_no_subjects(self):
#         '''Method to compute subjects.'''
#         contador = 0
#         for rec in self:
#              #nombre = rec.standard_id.student_ids[0].student_code
#              contador = len(rec.subject_ids)

#         return contador
#     #-----------------------------------------------------------------------#
#     def generate_encuentros(self, no_subjects):
#         """Generate Encuentros por seccion / Curso."""

#         i = 1
        
#         no_encuentros = 0

#         asistencia_obj = self.env['subject.asistencia']

#         for rec in self:
#             if no_subjects != 0:
#                while i <= no_subjects:
                   
#                    sta_id = rec.id
#                    use_id = rec.user_id.id
#                    sub_id = rec.subject_ids[i-1].id
#                    no_encuentros = len(rec.subject_ids[i-1].encuentro_ids)
#                    j = 1

#                    while j <= no_encuentros:
                        
#                         enc_id = rec.subject_ids[i-1].encuentro_ids[j-1].id
#                         aux_desc = rec.subject_ids[i-1].encuentro_ids[j-1].description

#                         asistencia_obj.create({
#                             'standard_id' : sta_id,
#                             'subject_id'  : sub_id,
#                             'teacher_id'  : use_id,
#                             'encuentro_id': enc_id,
#                             'description' : aux_desc,
                            
#                         })

#                         j = j + 1

#                    i = i + 1
#     #-----------------------------------------------------------------------# 
#     # GENERA LAS EVALUACIONES#
#     #-----------------------------------------------------------------------#
#     def generate_evaluaciones(self, no_subjects):
#         """Generate Encuentros por seccion / Curso."""

#         i = 1
        
#         no_eva = 0

#         evaluacion_obj = self.env['subject.evaluacion']

#         for rec in self:
#             if no_subjects != 0:
#                while i <= no_subjects:
                   
#                    sta_id = rec.id
#                    use_id = rec.user_id.id
#                    sub_id = rec.subject_ids[i-1].id
#                    no_eva = len(rec.subject_ids[i-1].evaluacion_ids)
#                    j = 1

#                    while j <= no_eva:
                        
#                         enc_id = rec.subject_ids[i-1].evaluacion_ids[j-1].id
#                         aux_desc = rec.subject_ids[i-1].evaluacion_ids[j-1].description

#                         evaluacion_obj.create({
#                             'standard_id' : sta_id,
#                             'subject_id'  : sub_id,
#                             'teacher_id'  : use_id,
#                             'evaluacion_id': enc_id,
#                             'description' : aux_desc,
                            
#                         })

#                         j = j + 1

#                    i = i + 1
#    #-----------------------------------------------------------------------# 

#     @api.onchange('standard_id', 'division_id')
#     def onchange_combine(self):
#         '''Onchange to assign name respective of it's standard and division'''
#         self.name = str(self.standard_id.name
#                         ) + '-' + str(self.division_id.name)

#     #@api.constrains('standard_id', 'division_id')
#     #def check_standard_unique(self):
#     #    """Method to check unique standard."""
#     #    if self.env['school.standard'].search([
#     #                            ('standard_id', '=', self.standard_id.id),
#     #                            ('division_id', '=', self.division_id.id),
#     #                            ('school_id', '=', self.school_id.id),
#     #                            ('id', 'not in', self.ids)]):
#     #        raise ValidationError(_("Division and class should be unique!"))
#     @api.constrains('standard_id', 'division_id')
#     def check_standard_unique(self):
#         """Method to check unique standard."""
#         if self.env['school.standard'].search([
                                
#                                 ('code', '=', self.code),
#                                 ('school_id', '=', self.school_id.id),
#                                 ('id', 'not in', self.ids)]):
#             raise ValidationError(_("El còdigo de la secciòn debe ser ùnico en el campus!"))
  
#     # def unlink(self):
#     #     """Method to check unique standard."""
#     #     for rec in self:
#     #         if rec.student_ids or rec.subject_ids or rec.syllabus_ids:
#     #             raise ValidationError(_(
#     # "You cannot delete as it has reference with student, subject or syllabus!"))
#     #     return super(SchoolStandard, self).unlink()

#     @api.constrains('capacity')
#     def check_seats(self):
#         """Method to check seats."""
#         if self.capacity <= 0:
#             raise ValidationError(_("Total seats should be greater than 0!"))

#     def name_get(self):
#         '''Method to display standard and division'''
#         return [(rec.id, rec.standard_id.name + '-' + '[' + rec.division_id.name + ']' + '[' + rec.code + ']') for rec in self]

class SchoolSchool(models.Model):
    ''' Defining School Information'''

    _name = 'school.school'
    _description = 'School Information'
    _rec_name = "com_name"

    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if self.env["school.school"].search(
                [('code', '=', record.code), ('id', '!=', record.id)]):
                raise ValidationError("School Código must be Unique")

    @api.model
    def _lang_get(self):
        '''Method to get language'''
        languages = self.env['res.lang'].search([])
        return [(language.code, language.name) for language in languages]

    company_id = fields.Many2one('res.company', 'Company', ondelete="cascade",
                                 required=True, delegate=True,
                                 help='Company_id of the school')
    com_name = fields.Char('School Nombre', related='company_id.name',
                           store=True, help='Sede name')
    code = fields.Char('Código', required=True, help='Sede code')
    standards = fields.One2many('school.standard', 'school_id',
                                'Standards', help='Sede standard')
    lang = fields.Selection(_lang_get, 'Lenguaje',
                            help='''If the selected language is loaded in the
                                system, all documents related to this partner
                                will be printed in this language.
                                If not, it will be English.''')
    required_age = fields.Integer("Edad Mínima de Admisión", default=6,
                                  help='''Minimum required age for 
                                  student admission''')

    @api.model
    def create(self, vals):
        '''Inherited create method to assign company_id to school'''
        res = super(SchoolSchool, self).create(vals)
        main_company = self.env.ref('base.main_company')
        res.company_id.parent_id = main_company.id
        return res


# class SubjectSubject(models.Model):
    # '''Defining a subject '''
    # _name = "subject.subject"
    # _description = "Subjects"

    # name = fields.Char('Nombre', required=True, help='Subject name')
    # code = fields.Char('Código', required=True, help='Subject code')
    # maximum_marks = fields.Integer("Calificación máxima",
    #                                help='Calificación máxima of the subject can get')
    # minimum_marks = fields.Integer("Calificación mínima", help='''Required minimum
    #                                                  marks of the subject''')
    
    # nro_encuentros = fields.Integer("Nros. Encuentros", required=True, default=1 ,help='''Indica el número de encuentros que requiere el CURSO''')
    # nro_eva        = fields.Integer("Nros. Evaluaciones", required=True, default=1 ,help='''Indica el número de evaluaciones que requiere el CURSO''')

    # weightage = fields.Integer("WeightAge", help='Weightage of the subject')
    # teacher_ids = fields.Many2many('school.teacher', 'subject_teacher_rel',
    #                                'subject_id', 'teacher_id', 'Teachers',
    #                                help='Teachers of the following subject')
    # standard_ids = fields.Many2many('standard.standard', string='Standards',
    #                                 help='''Standards in which the 
    #                                 following subject taught''')
    # standard_id = fields.Many2one('standard.standard', 'Class',
    #                               help='''Class in which the following
    #                               subject taught''')
    # is_practical = fields.Boolean('Es Práctica?',
    #                               help='Check this if subject is practical.')
    # elective_id = fields.Many2one('subject.elective',
    #                               help='''Elective subject respective
    #                               the following subject''')
    # student_ids = fields.Many2many('student.student',
    #                                'elective_subject_student_rel',
    #                                'subject_id', 'student_id', 'Students',
    #                                help='Students who choose this subject')
    # #-----------------------------------------------------------------------#
    # # DESARROLLO PROPIO: SE AGREGO ESTE CAMPO                               #
    # #-----------------------------------------------------------------------# 
    # encuentro_ids = fields.One2many('subject.encuentros', 'subject_id', string="Encuentros")
    # evaluacion_ids = fields.One2many('subject.planevaluacion', 'subject_id', string="Evaluaciones")
    # #-----------------------------------------------------------------------#
    # @api.constrains("maximum_marks", "minimum_marks")
    # def check_marks(self):
    #     """Method to check marks."""
    #     if self.minimum_marks >= self.maximum_marks:
    #         raise ValidationError(
    #             _("Configure Calificación máxima greater than minimum marks!"))

    # @api.model
    # def _search(
    #     self, args, offset=0, limit=None, order=None, count=False,
    #     access_rights_uid=None, ):
    #     """Override method to get exam of subject selection."""
    #     if self._context.get("is_from_subject_report") and \
    #         self._context.get("active_model") and \
    #         self._context.get("active_id"):

    #         teacher_rec = self.env[self._context.get("active_model")].browse(
    #             self._context.get("active_id"))
    #         sub_ids = [sub_id.id for sub_id in teacher_rec.subject_id]
    #         args.append(("id", "in", sub_ids))
    #     return super(SubjectSubject, self)._search(args=args, offset=offset,
    #         limit=limit, order=order, count=count,
    #         access_rights_uid=access_rights_uid, )
    
 #-----------------------------------------------------------------------#
 # DESARROLLO PROPIO: SE AGREGO ESTA CLASE                               #
 #-----------------------------------------------------------------------# 
    
# class SubjectEncuentros(models.Model):
#     _name = "subject.encuentros"
#     _description = "Cursos / Encuentros"

#     name = fields.Char(string='Nombre', store=True, required=True)
#     code = fields.Char('Código', required=True, help='Código/Secuencia del encuentro')
#     description = fields.Text('Descripción', help='Descripción')

#     subject_id = fields.Many2one('subject.subject', string="Curso")
# #-----------------------------------------------------------------------#

    
# class SubjectPlanEvaluacion(models.Model):
#     _name = "subject.planevaluacion"
#     _description = "Cursos / Plan / Evaluacion"

#     name = fields.Char(string='Nombre', store=True, required=True)
#     code = fields.Char('Código', required=True, help='Código/Secuencia de la Evaluación')
#     description = fields.Text('Descripción', help='Descripción')

#     subject_id = fields.Many2one('subject.subject', string="Curso")
# #-----------------------------------------------------------------------#


# class SubjectSyllabus(models.Model):
#     '''Defining a  syllabus'''
#     _name = "subject.syllabus"
#     _description = "Syllabus"
#     _rec_name = "subject_id"

#     standard_id = fields.Many2one('school.standard', 'Standard',
#                                 help='Standard which had this subject')
#     subject_id = fields.Many2one('subject.subject', 'Subject', help='Subject')
#     syllabus_doc = fields.Binary("Syllabus Doc",
#                                 help="Attach syllabus related to Subject")


# class SubjectElective(models.Model):
#     ''' Defining Subject Elective '''
#     _name = 'subject.elective'
#     _description = "Elective Subject"

#     name = fields.Char("Nombre", help='Elective subject name')
#     subject_ids = fields.One2many('subject.subject', 'elective_id',
#         'Elective Subjects',
#         help="Subjects of the respective elective subject")


class MotherTongue(models.Model):
    """Defining mother tongue."""

    _name = 'mother.toungue'
    _description = "Mother Toungue"

    name = fields.Char("Mother Tongue", help='Lenguaje name')


class StudentAward(models.Model):
    """Defining student award."""

    _name = 'student.award'
    _description = "Student Awards"

    award_list_id = fields.Many2one('student.student', 'Student',
                                help='Students who about to get the award')
    name = fields.Char('Award Nombre', help='Award name')
    description = fields.Char('Descripción', help='Descripción')


class AttendanceType(models.Model):
    """Defining attendance type."""

    _name = "attendance.type"
    _description = "School Type"

    name = fields.Char('Nombre', required=True, help='Attendance type name')
    code = fields.Char('Código', required=True, help='Attendance type code')


class StudentDocument(models.Model):
    """Defining Student document."""
    _name = 'student.document'
    _description = "Student Document"
    _rec_name = "doc_type"

    doc_id = fields.Many2one('student.student', 'Student',
                            help='Student of the following doc')
    file_no = fields.Char('File No', readonly="1",
        default=lambda obj: obj.env['ir.sequence'
            ].next_by_code('student.document'),
            help='File no of the document')
    submited_date = fields.Date('Submitted Date',
                                help='Document submitted date')
    doc_type = fields.Many2one('document.type', 'Document Type', required=True,
            help='Document type')
    file_name = fields.Char('File Nombre', help='File name')
    return_date = fields.Date('Return Date', help='Document return date')
    new_datas = fields.Binary('Attachments', help='Attachments of the document')


class DocumentType(models.Model):
    ''' Defining a Document Type(SSC,Leaving)'''
    _name = "document.type"
    _description = "Document Type"
    _rec_name = "doc_type"
    _order = "seq_no"

    seq_no = fields.Char('Correlativo', readonly=True,
        default=lambda self: _('New'), help='Correlativo of the document')
    doc_type = fields.Char('Document Type', required=True,
        help='Document type')

    @api.model
    def create(self, vals):
        if vals.get('seq_no', _('New')) == _('New'):
            vals['seq_no'] = self.env['ir.sequence'].next_by_code(
                        'document.type') or _('New')
        return super(DocumentType, self).create(vals)


class StudentDescription(models.Model):
    ''' Defining a Student Description'''
    _name = 'student.description'
    _description = "Student Description"

    des_id = fields.Many2one('student.student', 'Student Ref.',
                help='Student record from students')
    name = fields.Char('Nombre', help='Descripción name')
    description = fields.Char('Descripción', help='Student description')


class StudentDescipline(models.Model):
    """Definign student dscipline."""

    _name = 'student.descipline'
    _description = "Student Discipline"

    student_id = fields.Many2one('student.student', 'Student',
                help='Student')
    teacher_id = fields.Many2one('school.teacher', 'Teacher',
                help='Teacher who examine the student')
    date = fields.Date('Date', help='Date')
    class_id = fields.Many2one('standard.standard', 'Class',
                help='Class of student')
    note = fields.Text('Note', help='Discipline Note')
    action_taken = fields.Text('Action Taken',
                help='Action taken against discipline')


class StudentHistory(models.Model):
    """Defining Student History."""

    _name = "student.history"
    _description = "Student History"

    student_id = fields.Many2one('student.student', 'Student',
                help='Related Student')
    academice_year_id = fields.Many2one('academic.year', 'Lapso Académico',
                help='Academice Year')
    standard_id = fields.Many2one('school.standard', 'Standard',
                help='Standard of the following student')
    percentage = fields.Float("Percentage", readonly=True,
                help='Percentage of the student')
    result = fields.Char('Result', readonly=True,
                help='Result of the student')


class StudentCertificate(models.Model):
    """Defining student certificate."""

    _name = "student.certificate"
    _description = "Student Certificate"

    student_id = fields.Many2one('student.student', 'Student',
                help='Related student')
    description = fields.Char('Descripción', help='Descripción')
    certi = fields.Binary('Certificate', required=True,
                help='Student certificate')


class StudentReference(models.Model):
    ''' Defining a student reference information '''

    _name = "student.reference"
    _description = "Student Reference"

    reference_id = fields.Many2one('student.student', 'Student',
                help='Student reference')
    name = fields.Char('First Nombre', required=True,
                help='Student name')
    middle = fields.Char('Middle Nombre', required=True,
                help='Student middle name')
    last = fields.Char('Surname', required=True,
                help='Student last name')
    designation = fields.Char('Designation', required=True,
                help='Student designation')
    phone = fields.Char('Phone', required=True,  help='Student phone')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')],
                'Gender',  help='Student gender')


class StudentPreviousSchool(models.Model):
    ''' Defining a student previous school information '''
    _name = "student.previous.school"
    _description = "Student Previous Sede"

    previous_school_id = fields.Many2one('student.student', 'Student',
                                         help='Related student')
    name = fields.Char('Nombre', required=True,
            help='Student previous school name')
    registration_no = fields.Char('Registration No.', required=True,
            help='Student registration number')
    admission_date = fields.Date('Admission Date',
            help='Student admission date')
    exit_date = fields.Date('Exit Date',
            help='Student previous school exit date')
    course_id = fields.Many2one('standard.standard', 'Course', required=True,
            help='Student gender')
    add_sub = fields.One2many('academic.subject', 'add_sub_id', 'Add Subjects',
            help='Student gender')

    @api.constrains('admission_date', 'exit_date')
    def check_date(self):
        new_dt = fields.Date.today()
        if (self.admission_date and self.admission_date >= new_dt) or (
            self.exit_date and self.exit_date >= new_dt):
            raise ValidationError(_(
        "Your admission date and exit date should be less than current date!"))
        if (self.admission_date and self.exit_date) and (
            self.admission_date > self.exit_date):
            raise ValidationError(_(
        "Admission date should be less than exit date in previous school!"))


class AcademicSubject(models.Model):
    ''' Defining a student previous school information '''
    _name = "academic.subject"
    _description = "Student Previous School"

    add_sub_id = fields.Many2one('student.previous.school', 'Add Subjects',
                                 invisible=True,
                                 help='Select student previous school')
    name = fields.Char('Nombre', required=True,
                       help='Enter previous school name')
    maximum_marks = fields.Integer("Calificación máxima", help='Enter maximum mark')
    minimum_marks = fields.Integer("Calificación mínima", help='Enter minimum marks')


class StudentFamilyContact(models.Model):
    ''' Defining a student emergency contact information '''
    _name = "student.family.contact"
    _description = "Student Family Contact"

    @api.depends('relation', 'stu_name')
    def _compute_get_name(self):
        for rec in self:
            relative_name = rec.name
            if rec.stu_name:
                rec.relative_name = rec.stu_name.name
            rec.relative_name = relative_name

    family_contact_id = fields.Many2one('student.student', 'Student Ref.',
                                        help='Enter related student')
    rel_name = fields.Selection([('exist', 'Link to Existing Student'),
                                 ('new', 'Create New Relative Nombre')],
                                'Related Student', help="Select Nombre",
                                required=True)
    user_id = fields.Many2one('res.users', 'User ID', ondelete="cascade",
                              help='Enter related user of the student')
    stu_name = fields.Many2one('student.student', 'Existing Student',
                               help="Select Student From Existing List")
    name = fields.Char('Relative Nombre', help='Enter relative name')
    relation = fields.Many2one('student.relation.master', 'Relation',
                               required=True,
                               help='Select student relation with member')
    phone = fields.Char('Phone', required=True,
                        help='Enter family member contact')
    email = fields.Char('E-Mail', help='Enter student email')
    relative_name = fields.Char(compute='_compute_get_name', string='Nombre',
                                help='Enter student family member name')


class StudentRelationMaster(models.Model):
    ''' Student Relation Information '''
    _name = "student.relation.master"
    _description = "Student Relation Master"

    name = fields.Char('Nombre', required=True, help="Enter Relation name")
    seq_no = fields.Integer('Correlativo', help='Relation sequence')


class GradeMaster(models.Model):
    """Defining grade master."""

    _name = 'grade.master'
    _description = "Grade Master"

    name = fields.Char('Grade', required=True, help='Grade name')
    company_id   = fields.Many2one('res.company', 'Companía', required=True, help='Companía')
    state        = fields.Selection([('draft', 'Draft'), 
                                     ('done', 'Done'),
                                     ('terminate', 'Terminate'), 
                                     ('cancel', 'Cancel')], 
                                     'Status', default="draft", tracking=True, help='State of the student registration form')


    grade_ids = fields.One2many('grade.line', 'grade_id', 'Grade Lines', help='Grade which are consider in this.')

    #--------------------------------------------------------------------------------
    def set_terminate(self):
        '''Set the state to terminate'''

        # if self.validar_evaluaciones():
        #     if self.validar_actividades():
        #         self.state = 'terminate'
        #     else:
        #         raise ValidationError(_("El total de la ponderación de las actividades debe ser igual a 100% "))
        # else:
        #     raise ValidationError(_("El total de la ponderación de las evaluaciones debe ser igual a 100% "))
        self.state = 'terminate'

    #--------------------------------------------------------------------------------       
    def set_iniciado(self):
        '''Set the state to terminate'''

        self.state = 'draft'
#--------------------------------------------------------------------------------       

class GradeLine(models.Model):
    """Defining grade line."""

    _name = 'grade.line'
    _description = "Grades"
    _rec_name = 'grade'

    base_mark = fields.Integer('Escala Base', required=True,
            help='The grade will starts from this marks.')
    from_mark = fields.Integer('Escala Inferior', required=True,
            help='The grade will starts from this marks.')
    to_mark = fields.Integer('Escala Superior', required=True,
            help='The grade will ends to this marks.')
    
    pass_mark = fields.Integer('Calificaciòn de Aprobaciòn', required=True,
            help='The grade will ends to this marks.')
    
    grade = fields.Char('Nivel', required=True, help="Grade")
    sequence = fields.Integer('Correlativo', help="Correlativo order of the grade.")
    fail = fields.Boolean('Cero', help='''If fail field is set to True,
it will allow you to set the grade as fail.''')
    grade_id = fields.Many2one("grade.master", 'Grade Ref.',
            help='Related grade')
    name = fields.Char('Nombre', help='Grade name')
    state        = fields.Selection([('draft', 'Draft'), 
                                     ('done', 'Done'),
                                     ('terminate', 'Terminate'), 
                                     ('cancel', 'Cancel')], 
                                     'Status', default="draft", related='grade_id.state', tracking=True, help='State of the student registration form')

    @api.constrains('base_mark')
    def check_base_mark(self):
        """Method to check seats."""
        if self.base_mark <= 0:
           raise ValidationError(_("El valor de la ESCALA BASE debe ser mayor a 0"))

    @api.constrains('from_mark')
    def check_from_mark(self):
        """Method to check seats."""
        if self.from_mark < 0:
           raise ValidationError(_("El valor de la ESCALA INFERIOR debe ser mayor a 0"))

    @api.constrains('to_mark')
    def check_pass_mark(self):
        """Method to check seats."""
        if self.to_mark < self.from_mark or self.to_mark > self.base_mark:
           raise ValidationError(_("El valor de la ESCALA SUPERIOR debe estar entre la ESCALA INFERIOR y LA ESCALA BASE"))


    @api.constrains('pass_mark')
    def check_pass_mark(self):
        """Method to check seats."""
        if self.pass_mark <= 0 or self.pass_mark > self.base_mark:
           raise ValidationError(_("El valor de la ESCALA DE APROBACIÓN debe estar entre la ESCALA INFERIOR y LA ESCALA BASE"))


    @api.constrains('from_mark', 'to_mark')
    def check_marks(self):
        '''Method to check overlapping of Marks'''
        for rec in self:
            if (rec.to_mark < rec.from_mark):
                raise ValidationError(_(
            "To Marks should be greater than From Marks!"))
            for line in self.search([('grade_id', '=', rec.grade_id.id),
                                    ('id', '!=', rec.id)]):
                if (line.from_mark <= rec.from_mark <= line.to_mark or
                    line.from_mark <= rec.to_mark <= line.to_mark):
                    raise ValidationError(_(
                            "Error! You cannot define overlapping Marks!"))


class StudentNews(models.Model):
    """Defining studen news."""

    _name = 'student.news'
    _description = 'Student News'
    _rec_name = 'subject'
    _order = 'date asc'

    subject = fields.Char('Subject', required=True,
                          help='Subject of the news.')
    description = fields.Text('Descripción', help="Descripción")
    date = fields.Datetime('Expiry Date', help='Expiry date of the news.')
    user_ids = fields.Many2many('res.users', 'user_news_rel', 'id', 'user_ids',
            'User News', help='Nombre to whom this news is related.')
    color = fields.Integer('Color Index', default=0, help='Color index')

    @api.constrains("date")
    def checknews_dates(self):
        """Check news date."""
        new_date = fields.datetime.today()
        if self.date < new_date:
            raise ValidationError(_(
"Configure expiry date greater than current date!"))

    def news_update(self):
        '''Method to send email to student for news update'''
        emp_obj = self.env['hr.employee']
        obj_mail_server = self.env['ir.mail_server']
        user = self.env.user
        # Check if out going mail configured
        mail_server_record = obj_mail_server.search([],limit=1)
        if not mail_server_record:
            raise UserError(_('''User Email Configuration!
"Outgoing mail server not specified!'''))
        email_list = []
        # Check email is defined in student
        for news in self:
            if news.user_ids and news.date:
                email_list = [news_user.email for news_user in news.user_ids
                              if news_user.email]
                if not email_list:
                    raise UserError(_('''User Email Configuration!,
Email not found in users!'''))
            # Check email is defined in user created from employee
            else:
                for employee in emp_obj.search([]):
                    if employee.work_email:
                        email_list.append(employee.work_email)
                    elif employee.user_id and employee.user_id.email:
                        email_list.append(employee.user_id.email)
                if not email_list:
                    raise UserError(_('''Email Configuration!,
Email not defined!'''))
            news_date = news.create_date
            # Add company name while sending email
            company = user.company_id.name or ''
            body = """Hi,<br/><br/>
                    This is a news update from <b>%s</b> posted at %s<br/>
                    <br/> %s <br/><br/>
                    Thank you.""" % (company,
                news_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                news.description or '')
            smtp_user = mail_server_record.smtp_user or False
            # Check if mail of outgoing server configured
            if not smtp_user:
                raise UserError(_('''Email Configuration,
Kindly,Configure Outgoing Mail Server!'''))
            notification = 'Notification for news update.'
            # Configure email
            message = obj_mail_server.build_email(email_from=smtp_user,
                email_to=email_list, subject=notification, body=body,
                body_alternative=body, reply_to=smtp_user, subtype='html')
            # Send Email configured above with help of send mail method
            obj_mail_server.send_email(message=message,
                                       mail_server_id=mail_server_ids[0].id)
        return True


class StudentReminder(models.Model):
    """Defining student reminder."""

    _name = 'student.reminder'
    _description = "Student Reminder"

    @api.model
    def check_user(self):
        '''Method to get default value of logged in Student'''
        return self.env['student.student'].search([
                                        ('user_id', '=', self._uid)]).id

    stu_id = fields.Many2one('student.student', 'Student Nombre', required=True,
                            default=check_user, help='Relative student')
    name = fields.Char('Title', help='Reminder name')
    date = fields.Date('Date', help='Reminder date')
    description = fields.Text('Descripción',
                            help='Descripción of the reminder')
    color = fields.Integer('Color Index', default=0, help='Color index')

    @api.constrains("date")
    def check_date(self):
        """Method to check constraint of due date and assign date"""
        if self.date < fields.Date.today():
            raise ValidationError(_(
                "Reminder date of must be greater or equal current date !"))

class StudentCast(models.Model):
    """Defining student cast."""

    _name = "student.cast"
    _description = "Student Cast"

    name = fields.Char("Nombre", required=True, help='Student cast')


class ClassRoom(models.Model):
    """Defining class room."""

    _name = "class.room"
    _description = "Class Room"

    name = fields.Char("Nombre", help='Class room name')
    number = fields.Char("Salón Nro.", help='Class room number')
    school_id = fields.Many2one('school.campus', 'Campus', help='Select Campus', required=True, tracking=True)


class Report(models.Model):
    _inherit = "ir.actions.report"

    def render_template(self, template, values=None):
        student_id = self._context.get('student_id')
        if student_id:
            student_rec = self.env['student.student'].browse(student_id)
        if student_rec and student_rec.state == 'draft':
            raise ValidationError(_(
                    "You cannot print report forstudent in unconfirm state!"))
        return super(Report, self).render_template(template, values)
