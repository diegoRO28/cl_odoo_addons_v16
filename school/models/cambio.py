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
            if record.standard_id.remaining_seats<=0:
                raise ValidationError("Error: La sección no tiene cupos disponibles..!")     
            
#-----------------------------------------------------------------------#
    @api.constrains('standard_des_id')
    def _check_sec_des(self):
         for record in self:
            if record.standard_id == record.standard_des_id:
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
    standard_des_id  = fields.Many2one('school.standard', 'Sección', help='Select student standard', tracking=True)
    subject_des_id   = fields.Many2one('subject.subject', 'Curso', related='standard_des_id.subject_id', required=True, help='Curso')
    company_des_id   = fields.Many2one('res.company', 'Companía', related='standard_des_id.company_id', store=True, help='Company_id of the school')
    remaining_seats_destino = fields.Integer(
        string='Cupos Disponibles',
        related='standard_des_id.remaining_seats',
        readonly=True
    )
    seccion_origen_hist = fields.Many2one(
        'school.standard',
        string='Sección Origen',
        compute='_compute_seccion_origen_hist',
        store=True,
        readonly=True,
        help='Sección en la que estaba el estudiante al momento del cambio '
             '(se calcula una sola vez, al crear el registro, y queda fija).',
    )

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

    @api.depends('student_id', 'ri_id', 'cambio_date')
    def _compute_seccion_origen_hist(self):
        for rec in self:
            # El origen de ESTE cambio es, simplemente, la sección que la
            # inscripción (ri_id) tiene en este preciso momento -- antes de
            # que ESTE cambio la sobreescriba. Como siempre reutilizamos la
            # MISMA inscripción en toda la cadena, esto es fiable tanto para
            # el primer cambio como para cualquiera de los siguientes, y no
            # depende de comparar 'cambio_date' (que puede repetirse el
            # mismo día y romper la búsqueda del cambio anterior).
            rec.seccion_origen_hist = rec.ri_id.standard_id

    @api.onchange('student_id')
    def _onchange_student_id(self):
        """Cuando se selecciona un estudiante, buscar su última inscripción activa y asignarla a ri_id."""
        if self.student_id:
            inscripcion_activa = self.env['student.inscripcion'].search([
                ('student_id', '=', self.student_id.id),
                ('state', '=', 'done')
            ], order='inscription_date desc', limit=1)
            if inscripcion_activa:
                # standard_id, school_id y move_id son campos related a ri_id.*
                # (no-stored y sin readonly=True): se llenan solos al asignar ri_id,
                # NO hay que reasignarlos a mano (eso puede escribir de vuelta sobre
                # la inscripción real vía el inverso del related).
                self.ri_id = inscripcion_activa
                # Sección origen: se fija explícitamente aquí (además del compute
                # con store=True) para que se vea de inmediato en pantalla, sea
                # el primer cambio o uno encadenado.
                self.seccion_origen_hist = inscripcion_activa.standard_id
            else:
                self.ri_id = False
                return {
                    'warning': {
                        'title': 'Sin inscripción activa',
                        'message': 'Este estudiante no tiene una inscripción activa. Debe inscribirlo primero.'
                    }
                }
        else:
            self.ri_id = False

    def _get_cambio_anterior(self):
        self.ensure_one()
        domain = [
            ('student_id', '=', self.student_id.id),
            ('state', '=', 'terminate'),
        ]
        # Ordenamos por 'id' (orden real de creación) en vez de 'cambio_date':
        # dos cambios pueden compartir la misma fecha (mismo día), y en ese
        # caso comparar por fecha no distingue cuál fue "antes" en la cadena.
        # El id sí lo hace de forma inequívoca.
        if self._origin.id:
            domain.append(('id', '<', self._origin.id))
        return self.search(domain, order='id desc', limit=1)

    def _get_cambio_siguiente(self):
        """Devuelve el cambio siguiente (si existe) basado en la inscripción destino."""
        self.ensure_one()

        if self.state != 'terminate':
            return False

        domain = [
            ('student_id', '=', self.student_id.id),
            ('ri_id.standard_id', '=', self.standard_des_id.id),
            ('state', '=', 'terminate'),
        ]
        # Orden por 'id' en vez de 'cambio_date' por la misma razón que en
        # _get_cambio_anterior: la fecha puede repetirse el mismo día.
        if self._origin.id:
            domain.append(('id', '>', self._origin.id))
        cambio_siguiente = self.search(domain, order='id asc', limit=1)
        return cambio_siguiente

    def admission_done(self):
        for rec in self:
            seccion_origen = rec.seccion_origen_hist
            if not seccion_origen:
                raise ValidationError("No se encontró la sección origen.")
            if seccion_origen == rec.standard_des_id:
                raise ValidationError("Error: La sección ORIGEN y DESTINO deben ser diferentes.")
            if rec.standard_des_id.remaining_seats <= 0:
                raise ValidationError("Error: La sección destino no tiene cupos disponibles.")
            
            rec.state = 'terminate'
            cambio_siguiente = rec._get_cambio_siguiente()
            if not cambio_siguiente:
                self._actualizar_inscripcion(rec)
            
            seccion_origen._compute_total_student()
            rec.standard_des_id._compute_total_student()

    def _actualizar_inscripcion(self, rec):
        '''Actualiza la inscripción origen con los datos de la sección destino'''
        try:
            # Obtener la inscripción actual
            inscripcion = rec.ri_id
            if not inscripcion:
                raise ValidationError("No hay inscripción origen para actualizar.")

            # --- Capturar la sección ORIGEN antes de escribir ---
            # rec.standard_id es un related (ri_id.standard_id) sin store=True: si se lee
            # después del write(), ya devuelve la sección destino y no la que se está dejando.
            seccion_origen_real = inscripcion.standard_id

            # --- Actualizar la inscripción con los datos de la sección destino ---
            inscripcion.write({
                'standard_id': rec.standard_des_id.id,
                'school_id': rec.school_des_id.id,
                'inscription_date': rec.cambio_date,  # opcional: actualizar fecha
                'note': f'Cambio de sección realizado el {rec.cambio_date}. Origen: {rec.ri_id.standard_id.code}',
            })

            # --- Recalcular cupos ---
            # Se asume que al cambiar la sección, se ajustan los cupos automáticamente
            # Si no, puedes llamar a métodos específicos aquí
            if seccion_origen_real:
                seccion_origen_real._compute_total_student()  # origen (real, capturado antes del write)
            rec.standard_des_id._compute_total_student()  # destino

            # Actualizar el standard_id del cambio para que apunte a la nueva sección
            #rec.write({'standard_id': rec.standard_des_id.id})

            return inscripcion

        except Exception as error:
            raise ValidationError(f'Error al actualizar la inscripción: \n {error}')

    def action_ver_cadena_cambios(self):
        '''Abre la vista de todos los cambios encadenados para este estudiante'''
        self.ensure_one()
    
        # Obtener el primer cambio de la cadena
        cambios = []
        current = self
        while current:
            cambios.append(current.id)
            current = current._get_cambio_anterior()
        cambios.reverse()
    
        return {
            'type': 'ir.actions.act_window',
            'name': f'Cadena de Cambios - {self.student_id.display_name}',
            'res_model': 'student.cambio',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', cambios)],
        }

    def action_revertir_ultimo_cambio(self):
        self.ensure_one()
        if self.state != 'terminate':
            raise ValidationError(_("Solo se puede revertir un cambio en estado 'terminate'."))
        
        cambio_anterior = self._get_cambio_anterior()
        if not cambio_anterior:
            raise ValidationError(_("No se puede revertir el primer cambio de sección."))
        
        seccion_a_restaurar = cambio_anterior.standard_des_id
        if not seccion_a_restaurar:
            raise ValidationError(_("El cambio anterior no tiene sección destino definida."))
        
        inscripcion = self.ri_id
        if not inscripcion:
            raise ValidationError(_("No hay inscripción asociada a este cambio."))

        # --- Capturar la sección ACTUAL (la que el alumno está dejando) antes de escribir ---
        # self.standard_id es un related (ri_id.standard_id) sin store=True: si se lee
        # después del write(), ya devuelve la sección restaurada y nunca se libera el cupo
        # de la sección que realmente se está abandonando.
        seccion_actual = inscripcion.standard_id

        # Actualizar inscripción
        inscripcion.write({
            'standard_id': seccion_a_restaurar.id,
            'school_id': seccion_a_restaurar.school_id.id,
            'inscription_date': fields.Date.today(),
            'note': _('Reversión del cambio %s - restaurada sección %s') % (self.name, seccion_a_restaurar.display_name),
        })
        
        # Recalcular cupos
        if seccion_actual:
            seccion_actual._compute_total_student()
        if seccion_a_restaurar:
            seccion_a_restaurar._compute_total_student()
        
        # Guardar datos antes de eliminar
        student_id = self.student_id.id
        student_name = self.student_id.display_name
        
        # Eliminar el cambio actual
        self.unlink()
        
        # Mostrar lista de cambios del estudiante
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'student.cambio',
            'view_mode': 'tree,form',
            'domain': [('student_id', '=', student_id)],
            'target': 'current',
            'name': _('Cambios de %s') % student_name,
        }

    def action_nuevo_cambio(self):
        self.ensure_one()
        if self.state != 'terminate':
            raise ValidationError("Solo se puede crear un nuevo cambio a partir de un cambio ya confirmado (estado 'terminate').")
        
        vals = {
            'student_id': self.student_id.id,
            'ri_id': self.ri_id.id,
            'school_des_id': self.ri_id.school_id.id,
            'cambio_date': fields.Date.today(),
            'tipocambio_id': self.tipocambio_id.id,
            'note': self.note,
            'state': 'draft',
            # No se asigna standard_des_id, el usuario lo elegirá
        }
        nuevo = self.create(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'student.cambio',
            'res_id': nuevo.id,
            'view_mode': 'form',
            'target': 'current',
        }

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

        # --- Respaldo server-side: si ri_id no llegó del cliente (el onchange corre
        # en el navegador y puede no viajar en el payload final, sobre todo en campos
        # readonly), lo resolvemos aquí a partir del student_id, igual que hace
        # _onchange_student_id. Así el guardado no depende únicamente del cliente.
        if not vals.get('ri_id') and vals.get('student_id'):
            inscripcion_activa = self.env['student.inscripcion'].search([
                ('student_id', '=', vals['student_id']),
                ('state', '=', 'done')
            ], order='inscription_date desc', limit=1)
            if inscripcion_activa:
                vals['ri_id'] = inscripcion_activa.id

        if not vals.get('ri_id'):
            raise ValidationError(_(
                "No se pudo determinar la inscripción (RI) del estudiante. "
                "Verifique que el estudiante tenga una inscripción activa (estado 'Inscrito') "
                "antes de registrar el cambio de sección."
            ))

        res = super(StudentCambio, self).create(vals)
        return res