# See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

#--------------------------------------------------------------------------------
# LIBRO / EVALUACION (MASTER)
#--------------------------------------------------------------------------------
class SchoolLibroEvaluacion(models.Model):
    ''' Defining School Information'''

    _name        = 'school.libroeva'
    _description = 'Libro de Evaluacion'
    _order       = "nombre asc"
    _rec_name    = "nombre"
    _inherit     = ['mail.thread', 'mail.activity.mixin']

    #--------------------------------------------------------------------------------
    # VALIDACIONES
    #--------------------------------------------------------------------------------
    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if self.env["school.libroeva"].search(
                [('code', '=', record.code), ('id', '!=', record.id)]):
                raise ValidationError("El código debe ser único")

    #--------------------------------------------------------------------------------
    @api.depends('evaluacion_ids')
    def _compute_total_evaluaciones(self):
    
         for rec in self:

             rec.nro_evas = len(rec.evaluacion_ids)
             no_evas      = len(rec.evaluacion_ids)
             acum_eva     = 0
             i = 1
             while i <= no_evas:
                 acum_eva+= self.evaluacion_ids[i-1].porc_peso
                 i += 1

             rec.porc_plani = acum_eva    
         #raise ValidationError("Entro a depends")

    #--------------------------------------------------------------------------------
    # CAMPOS
    #--------------------------------------------------------------------------------
    name = fields.Char(string='Libro Nro.', required=True, copy=True, readonly=True, default=lambda self: _('New'))

    nombre       = fields.Char('Nombre', store=True,  help='Nombre del libro')
    code         = fields.Char('Código', required=True,  help='Code')
    grade_id     = fields.Many2one("grade.master", 'Escala de califiación',  help='Related grade')
    company_id   = fields.Many2one('res.company', 'Companía', related='grade_id.company_id', store=True, help='Company_id of the school')
 
    is_recupera  = fields.Boolean('¿Acepta recuperación?', default=True,  help="Indica la recuperación")
    nro_evas     = fields.Integer("Nro. evaluaciones", compute="_compute_total_evaluaciones", store=True, help='Total Evaluaciones')
    porc_peso    = fields.Integer("% Ponderación", default= 100, store=True, help='Total Evaluaciones')
    
    porc_plani   = fields.Integer("% Planificado", default= 0, store=True, help='% aprobación')
    porc_min_eva = fields.Integer("% Mínimo para una evaluación", default= 10, store=True, help='% aprobación')
    porc_max_eva = fields.Integer("% Máximo para una evaluación", default= 30, store=True, help='% aprobación')
    cant_min_eva = fields.Integer("Cantidad mínima de evaluaciones", default= 1, store=True, help='Cantidad Mínima de Evaluaciones')
    cant_max_eva = fields.Integer("Cantidad máxima de evaluaciones", default= 5, store=True, help='Cantidad Máxima de Evaluaciones')
    note         = fields.Text('Observaciones', help='Observaciones')
    state        = fields.Selection([('draft', 'Draft'), 
                                     ('done', 'Done'),
                                     ('terminate', 'Terminate'), 
                                     ('cancel', 'Cancel')], 
                                     'Status', default="draft", tracking=True, help='State of the student registration form')

    evaluacion_ids = fields.One2many('school.libroevas', 'libro_id', 'Evaluaciones', store=True, help='Students which are in this standard')

    #--------------------------------------------------------------------------------
    def set_terminate(self):
        '''Set the state to terminate'''

        if self.validar_evaluaciones():
            if self.validar_actividades():
                self.state = 'terminate'
            else:
                raise ValidationError(_("El total de la ponderación de las actividades debe ser igual a 100% "))
        else:
            raise ValidationError(_("El total de la ponderación de las evaluaciones debe ser igual a 100% "))
    #--------------------------------------------------------------------------------       
    def set_iniciado(self):
        '''Set the state to terminate'''

        self.state = 'draft'
    #--------------------------------------------------------------------------------    
    @api.constrains('porc_peso')
    def check_porc_peso(self):
        """Method to check seats."""
        if self.porc_peso != 100:
            raise ValidationError(_("El valor debe ser 100% "))
    #--------------------------------------------------------------------------------
    @api.model
    def create(self, vals):
          if vals.get('name', _('New')) == _('New'):
              vals['name'] = self.env['ir.sequence'].next_by_code('libroeva.code') or _('New')
          res = super(SchoolLibroEvaluacion, self).create(vals)
          return res

    #--------------------------------------------------------------------------------
    def validar_evaluaciones(self):
    
        for rec in self:

             rec.nro_evas = len(rec.evaluacion_ids)
             no_evas      = len(rec.evaluacion_ids)
             acum_eva     = 0
             i = 1
             while i <= no_evas:
                 acum_eva+= self.evaluacion_ids[i-1].porc_peso
                 i += 1

             if acum_eva != 100:
                return False
        return True

    #--------------------------------------------------------------------------------
    def validar_actividades(self):
    
        for rec in self:

             no_evas      = len(rec.evaluacion_ids)
             
             i = 1
             while i <= no_evas:
                 if self.evaluacion_ids[i-1].porc_plani != 100:
                    return False
                 i += 1
                
        return True


#--------------------------------------------------------------------------------
# LIBRO / EVALUACIONES (LINES)
#--------------------------------------------------------------------------------
class SchoolLibroEvaluaciones(models.Model):
    """Defining grade line."""

    _name        = 'school.libroevas'
    _description = "Libro / Evaluaciones"
    _order       = "id asc"

    #--------------------------------------------------------------------------------
    @api.depends('actividad_ids')
    def _compute_total_actividades(self):
    
         for rec in self:

             rec.nro_acts = len(rec.actividad_ids)
             no_acts      = len(rec.actividad_ids)
             acum_act     = 0
             i = 1
             while i <= no_acts:
                 acum_act+= self.actividad_ids[i-1].porc_peso
                 i += 1

             rec.porc_plani = acum_act    
         #raise ValidationError("Entro a depends")
    #--------------------------------------------------------------------------------
    name         = fields.Char(string='Eva. Nro.', required=True, copy=True, readonly=True, default=lambda self: _('New'))

    nombre       = fields.Char('Nombre', help='Escriba el nombre ')
    code         = fields.Char('Código', required=True, help='Code')
    porc_peso    = fields.Integer("% Ponderación ", store=True, help='% de Ponderación')
    nro_acts     = fields.Integer("Nro. actividades", compute="_compute_total_actividades", store=True, help='Total Evaluaciones')
    porc_plani   = fields.Integer("% Planificado", default= 0, store=True, help='% Planificado')
    
    is_recupera  = fields.Boolean('¿Acepta recuperación?', default=True, help="Indica la recuperación")
    note         = fields.Text('Observaciones', help='Observaciones')

    libro_id     = fields.Many2one("school.libroeva", 'Libro de evaluación', help='Related libro')

    actividad_ids = fields.One2many('school.libroact', 'evaluacion_id', 'Actividades', store=True, help='Students which are in this standard')
    
    state        = fields.Selection([('draft', 'Draft'), 
                                     ('done', 'Done'),
                                     ('terminate', 'Terminate'), 
                                     ('cancel', 'Cancel')], 
                                     'Status', default="draft", related='libro_id.state', tracking=True, help='State of the student registration form')

    @api.constrains('porc_peso')
    def check_porc_peso(self):
        """Method to check seats."""
        if self.porc_peso > 100 or self.porc_peso < 0:
           raise ValidationError(_("El valor debe estar entre 0 y 100% "))

    @api.model   
    def create(self, vals):
          if vals.get('name', _('New')) == _('New'):
              vals['name'] = self.env['ir.sequence'].next_by_code('libroevas.code') or _('New')
          res = super(SchoolLibroEvaluaciones, self).create(vals)
          return res

#--------------------------------------------------------------------------------
# LIBRO / ACTIVIDADES (LINES)
#--------------------------------------------------------------------------------
class SchoolLibroActividades(models.Model):
    """Defining grade line."""

    _name        = 'school.libroact'
    _description = "Libro / Actividades"
    _order       = "name asc"

    name          = fields.Char(string='Act. Nro.', required=True, copy=True, readonly=True, default=lambda self: _('New'))
    nombre        = fields.Char('Nombre', help='Escriba el Nombre')
    code          = fields.Char('Código', required=True, help='Code')
    tipo_id       = fields.Many2one("school.tipoeva", 'Tipo evaluación', help='Escriba el Tipo de Evaluación')
    porc_peso     = fields.Integer("% Ponderación", store=True, help='Total Evaluaciones')
        
    is_recupera   = fields.Boolean('¿Acepta recuperación?', related='tipo_id.is_recupera', help="Indica la recuperación")
    note          = fields.Text('Observaciones', help='Observaciones')

    evaluacion_id = fields.Many2one("school.libroevas", 'Libro de evaluaciones', help='Related libro')

    #--------------------------------------------------------------------------------
    @api.constrains('porc_peso')
    def check_porc_peso(self):
        """Method to check seats."""
        if self.porc_peso > 100 or self.porc_peso < 0:
           raise ValidationError(_("El valor debe estar entre 0 y 100% "))
    #--------------------------------------------------------------------------------
    @api.model
    def create(self, vals):
          if vals.get('name', _('New')) == _('New'):
              vals['name'] = self.env['ir.sequence'].next_by_code('libroact.code') or _('New')
          res = super(SchoolLibroActividades, self).create(vals)
          return res
    
 