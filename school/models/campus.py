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
            raise ValidationError(_("""This seems not to be valid email. Please enter email in correct format!"""))


class SchoolCampus(models.Model):
    ''' Defining School Information'''

    _name = 'school.campus'
    _description = 'School Information'
    #_rec_name = "com_name"

    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if self.env["school.campus"].search(
                [('code', '=', record.code), ('id', '!=', record.id)]):
                raise ValidationError("School Código must be Unique")

    company_id = fields.Many2one('res.company', 'Company', required=True, help='Company_id of the school')
    name = fields.Char('Nombre', store=True, help='Nombre del Campus')
    code = fields.Char('Código', required=True, help='Sede code')
    standards = fields.One2many('school.standard', 'school_id', 'Standards', help='Sede standard')
    required_age = fields.Integer("Edad Mínima de Admisión", default=6, help='''Minimum required age for student admission''')

    teacher_ids = fields.Many2many('school.teacher', 'campus_teacher_rel', 'campus_id', 'teacher_id', 'Teachers', help='Teachers of the following campus')

