from odoo import api, fields, models, tools, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import pytz

class StudentStudent(models.Model):

    _inherit = 'student.student'

    is_created_from_existing_contact = fields.Boolean(string='¿Es creado desde un contacto existente?')
    contact_id = fields.Many2one('res.partner', string='Contacto')
    created_from_contact_done = fields.Boolean(string='Registro desde contacto realizado')
    show_contact_id_field = fields.Boolean(string='Mostrar campo Contacto', compute='_compute_show_contact_id_field')
    show_contact_student_name_field = fields.Boolean(string='Mostrar campo Nombre para estudiante creado desde Contacto', compute='_compute_show_contact_student_name_field')

    @api.depends(
        'is_created_from_existing_contact', 
        'created_from_contact_done'
    )
    def _compute_show_contact_id_field(self):
        for rec in self:
            rec.show_contact_id_field = False
            if rec.is_created_from_existing_contact and not rec.created_from_contact_done:
                rec.show_contact_id_field = True

    @api.depends(
        'is_created_from_existing_contact', 
        'created_from_contact_done'
    )
    def _compute_show_contact_student_name_field(self):
        for rec in self:
            rec.show_contact_student_name_field = False
            if rec.is_created_from_existing_contact and rec.created_from_contact_done:
                rec.show_contact_student_name_field = True

    @api.onchange('contact_id')
    def _onchange_contact_id(self):
        for rec in self:
            rec.phone = rec.mobile = rec.email = rec.parent_street = rec.parent_street2 = rec.street = rec.street2 = False
            if rec.contact_id:
                if rec.contact_id.phone:
                    rec.phone = rec.contact_id.phone
                if rec.contact_id.mobile:
                    rec.mobile = rec.contact_id.mobile                    
                if rec.contact_id.email:
                    rec.email = rec.contact_id.email
                if rec.contact_id.parent_street:
                    rec.parent_street = rec.contact_id.parent_street
                if rec.contact_id.parent_street2:
                    rec.parent_street2 = rec.contact_id.parent_street2
                if rec.contact_id.street:
                    rec.street = rec.contact_id.street
                if rec.contact_id.street2:
                    rec.street2 = rec.contact_id.street2                                                                                                                        
                

    def _get_current_date(self):
        tz = self.env.context.get('tz') or 'UTC'  # Obteniendo la zona horaria del contexto de Odoo
        current_datetime = datetime.now(pytz.timezone(tz)) - timedelta(hours=4)  # Restando 4 horas a la fecha y hora actual
        return current_datetime.date()  # Retornando solo la fecha, sin la hora

    admission_date = fields.Date('Fecha de Inscripción', default=_get_current_date, help='Enter student admission date')
    allow_edit_admission_date = fields.Boolean('Permitir modificar la Fecha de Inscripción', compute='_compute_allow_edit_admission_date')

    @api.depends(
        'standard_id', 
        'standard_id.state'
    )
    def _compute_allow_edit_admission_date(self):
        for rec in self:
            rec.allow_edit_admission_date = True
            if rec.standard_id:
                if rec.standard_id.state == 'done':
                    rec.allow_edit_admission_date = False

class StudentStudent(models.Model):
    _inherit = 'student.student'

    is_created_from_existing_contact = fields.Boolean(string='¿Es creado desde un contacto existente?')
    created_from_contact_done = fields.Boolean(string='Registro desde contacto realizado')
    contact_id = fields.Many2one('res.partner', string='Contacto')

    # OVERRIDE:
    @api.model
    def create(self, vals):
        '''Method to create user when student is created'''
        if vals.get('pid', _('New')) == _('New'):
            vals['pid'] = self.env['ir.sequence'].next_by_code('student.student') or _('New')
        
        if vals.get('pid', False):
            vals['login'] = vals['pid']
            vals['password'] = vals['pid']
        else:
            raise UserError(_("Error! PID not valid so record will not be saved."))

        if vals.get('company_id', False):
            company_vals = {'company_ids': [(4, vals.get('company_id'))]}
            vals.update(company_vals)

        if vals.get('is_created_from_existing_contact') and vals.get('contact_id'):
            partner_id = self.env['res.partner'].browse(vals['contact_id'])
            if not partner_id:
                raise UserError(_("No se encontró el contacto con el ID proporcionado."))

            # Verificar si el contacto tiene un nombre
            if not partner_id.name:
                raise UserError(_("El contacto seleccionado no tiene un nombre. Por favor, asigne un nombre al contacto antes de continuar."))

            # Buscar o crear un usuario asociado al contacto
            user = self.env['res.users'].search([('partner_id', '=', partner_id.id)], limit=1)
            if not user:
                user = self.env['res.users'].create({
                    'name': partner_id.name,  # Asegurando que el nombre esté presente
                    'login': vals['pid'],
                    'email': vals['pid'],
                    'partner_id': partner_id.id
                })

            vals['user_id'] = user.id
            vals['name'] = partner_id.name
            # vals['partner_id'] = partner_id.id
            vals['created_from_contact_done'] = True
            
        res = super(StudentStudent, self).create(vals)

        teacher = self.env['school.teacher']
        for data in res.parent_id:
            for record in teacher.search([('stu_parent_id', '=', data.id)]):
                record.write({'student_id': [(4, res.id, None)]})
        
        # Assign group to student based on condition
        emp_grp = self.env.ref('base.group_user')
        if res.state == 'draft':
            admission_group = self.env.ref('school.group_school_student')
            new_grp_list = [admission_group.id, emp_grp.id]
            res.user_id.write({'groups_id': [(6, 0, new_grp_list)]})

            partner = False
            if res.is_created_from_existing_contact and res.contact_id:
                partner = res.contact_id
            else:
                partner = self.env['res.partner'].search([('id', '=', res.user_id.partner_id.id)])

            if partner:
                partner.student_id = res.id
                partner.is_student = True
            else:
                raise UserError(_( "No Encontro el PARTNER." + str(res.user_id.partner_id.id)))

        elif res.state == 'done':
            done_student = self.env.ref('school.group_school_student')
            group_list = [done_student.id, emp_grp.id]
            res.user_id.write({'groups_id': [(6, 0, group_list)]})

        return res

    # OVERRIDE:
    def write(self, vals):
        '''Inherited method write to assign 
        student to their respective teacher'''
        # Lógica original para asignar estudiantes a sus respectivos profesores:
        teacher = self.env['school.teacher']
        if vals.get('parent_id'):
            for parent in vals.get('parent_id')[0][2]:
                for data in teacher.search([('stu_parent_id', '=', parent)]):
                    data.write({'student_id': [(4, self.id)]})
        
        # Llamar al método write original para asegurarnos de que la lógica existente se ejecute:
        result = super(StudentStudent, self).write(vals)
        
        # Lógica adicional para actualizar el campo 'name' del 'user_id'
        if 'name' in vals:
            for student in self:
                if student.user_id:
                    student.user_id.write({'name': vals['name']})
        
        return result            