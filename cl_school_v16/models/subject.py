# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

class SubjectSubject(models.Model):
    '''Defining a subject '''
    _name        = "subject.subject"
    _rec_name    = "nombre"
    _description = "Subjects"

    #-----------------------------------------------------------------------#
    @api.depends('encuentro_ids')
    def _compute_total_encuentro(self):
        '''Method to compute total student.'''
        for rec in self:
            rec.nro_encuentros = len(rec.encuentro_ids)
    #-----------------------------------------------------------------------#

    @api.depends('evaluacion_ids')
    def _compute_total_evaluacion(self):
        '''Method to compute total student.'''
        for rec in self:
            rec.nro_evaluaciones = len(rec.evaluacion_ids)
    #-----------------------------------------------------------------------#

    name          = fields.Char(string='Curso', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    nombre        = fields.Char(string='Nombre', store=True, required=True)
    code          = fields.Char('Código', required=True, help='Subject code')
    maximum_marks = fields.Integer("Calificación máxima",
                                   help='Calificación máxima of the subject can get')
    minimum_marks = fields.Integer("Calificación mínima", help='''Required minimum
                                                     marks of the subject''')
    
    nro_encuentros = fields.Integer("Nros. Encuentros",   required=True, readonly=True, default=1 , compute="_compute_total_encuentro", help='''Indica el número de encuentros que requiere el CURSO''')
    nro_evaluaciones = fields.Integer("Nros. Evaluaciones", required=True, readonly=True, default=1 , compute="_compute_total_evaluacion" ,help='''Indica el número de evaluaciones que requiere el CURSO''')

    weightage = fields.Integer("WeightAge", help='Weightage of the subject')

    teacher_ids = fields.Many2many('school.teacher', 'subject_teacher_rel', 'subject_id', 'teacher_id', 'Teachers', help='Teachers of the following subject')
    
    standard_ids = fields.Many2many('standard.standard', string='Standards',
                                    help='''Standards in which the 
                                    following subject taught''')
    standard_id = fields.Many2one('standard.standard', 'Class',
                                  help='''Class in which the following
                                  subject taught''')
    is_practical = fields.Boolean('Es Práctica?',
                                  help='Check this if subject is practical.')
    elective_id = fields.Many2one('subject.elective',
                                  help='''Elective subject respective
                                  the following subject''')
    student_ids = fields.Many2many('student.student',
                                   'elective_subject_student_rel',
                                   'subject_id', 'student_id', 'Students',
                                   help='Students who choose this subject')

    code_moodle = fields.Char(string='Código Moodle', store=True)
    
    note = fields.Text('Observaciones', help='Observaciones')
    #-----------------------------------------------------------------------#
    # DESARROLLO PROPIO: SE AGREGO ESTE CAMPO                               #
    #-----------------------------------------------------------------------# 
    encuentro_ids = fields.One2many('subject.encuentros', 'subject_id', string="Encuentros")
    evaluacion_ids = fields.One2many('subject.planevaluacion', 'subject_id', string="Evaluaciones")

    #-----------------------------------------------------------------------#
    # V2                                                                    #
    #-----------------------------------------------------------------------# 
    programa_id = fields.Many2one('school.programa', 'Programa', required=True, help="Programa")
    libro_id = fields.Many2one('school.libroeva', 'Libro Evaluación', required=True, help='''Seleccione el libro de evaluación''')
    libroevas_ids = fields.One2many('school.libroevas', 'libro_id', related='libro_id.evaluacion_ids', string="Evaluaciones")
    state        = fields.Selection([('draft', 'Draft'), 
                                     ('done', 'Done'),
                                     ('terminate', 'Terminate'), 
                                     ('cancel', 'Cancel')], 
                                     'Status', default="draft", tracking=True, help='State of the student registration form')
    
    #--------------------------------------------------------------------------------
    def set_terminate(self):
        '''Set the state to terminate'''

       
        self.state = 'terminate'
 
    #-----------------------------------------------------------------------#       
    def set_iniciado(self):
        '''Set the state to terminate'''

        self.state = 'draft'
    #-----------------------------------------------------------------------#
    @api.model
    def create(self, vals):
          if vals.get('name', _('New')) == _('New'):
              vals['name'] = self.env['ir.sequence'].next_by_code('curso.code') or _('New')
          res = super(SubjectSubject, self).create(vals)
          return res
    #-----------------------------------------------------------------------#
    @api.constrains('code')
    def check_Duplicate_code(self):
       for rec in self:
             auxCode = self.env['subject.subject'].search([('code', '=', rec.code), ('id', '!=', rec.id)])
             
             if auxCode:
                 raise ValidationError(_("Còdigo del Curso %s ya existe" % rec.code))
    #-----------------------------------------------------------------------#
    @api.constrains("maximum_marks", "minimum_marks")
    def check_marks(self):
        """Method to check marks."""
        if self.minimum_marks >= self.maximum_marks:
            raise ValidationError(
                _("Configure Calificación máxima greater than minimum marks!"))
    #-----------------------------------------------------------------------#    
    def name_get(self):
        '''Method to display standard and division'''
        #return [(rec.id, rec.standard_id.name + '-' + '[' + rec.division_id.name + ']' + '[' + rec.code + ']') for rec in self]
        return [(rec.id, rec.nombre ) for rec in self]


   #@api.model
   # def _search(
   #     self, args, offset=0, limit=None, order=None, count=False,
   #     access_rights_uid=None, ):
        """Override method to get exam of subject selection."""
        # if self._context.get("is_from_subject_report") and \
        #     self._context.get("active_model") and \
        #     self._context.get("active_id"):

        #     teacher_rec = self.env[self._context.get("active_model")].browse(
        #         self._context.get("active_id"))
        #     sub_ids = [sub_id.id for sub_id in teacher_rec.subject_id]
        #     args.append(("id", "in", sub_ids))
        # return super(SubjectSubject, self)._search(args=args, offset=offset,
        #     limit=limit, order=order, count=count,
        #     access_rights_uid=access_rights_uid, )
    
 #-----------------------------------------------------------------------#
 # DESARROLLO PROPIO: SE AGREGO ESTA CLASE                               #
 #-----------------------------------------------------------------------# 
class SubjectEncuentros(models.Model):
    _name = "subject.encuentros"
    _description = "Cursos / Encuentros"

    name = fields.Char(string='Nombre', store=True, required=True)
    code = fields.Char('Código', required=True, help='Código/Secuencia del encuentro')
    description = fields.Text('Descripción', help='Descripción')

    subject_id = fields.Many2one('subject.subject', string="Curso")
#-----------------------------------------------------------------------#

    
class SubjectPlanEvaluacion(models.Model):
    _name = "subject.planevaluacion"
    _description = "Cursos / Plan / Evaluacion"

    name = fields.Char(string='Nombre', store=True, required=True)
    code = fields.Char('Código', required=True, help='Código/Secuencia de la Evaluación')
    description = fields.Text('Descripción', help='Descripción')

    subject_id = fields.Many2one('subject.subject', string="Curso")
#-----------------------------------------------------------------------#

class SubjectSyllabus(models.Model):
    '''Defining a  syllabus'''
    _name = "subject.syllabus"
    _description = "Syllabus"
    _rec_name = "subject_id"

    standard_id = fields.Many2one('school.standard', 'Standard',
                                help='Standard which had this subject')
    subject_id = fields.Many2one('subject.subject', 'Subject', help='Subject')
    syllabus_doc = fields.Binary("Syllabus Doc",
                                help="Attach syllabus related to Subject")


class SubjectElective(models.Model):
    ''' Defining Subject Elective '''
    _name = 'subject.elective'
    _description = "Elective Subject"

    name = fields.Char("Nombre", help='Elective subject name')
    subject_ids = fields.One2many('subject.subject', 'elective_id',
        'Elective Subjects',
        help="Subjects of the respective elective subject")