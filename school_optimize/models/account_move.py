# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, timedelta
import pytz
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):

    _inherit = 'account.move'

    def _get_current_date(self):
        tz = self.env.context.get('tz') or 'UTC'  # Obteniendo la zona horaria del contexto de Odoo
        current_datetime = datetime.now(pytz.timezone(tz)) - timedelta(hours=4)  # Restando 4 horas a la fecha y hora actual
        return current_datetime.date()  # Retornando solo la fecha, sin la hora

    # OVERRIDE: Por defecto, debe tener la fecha actual:
    # === Date fields === #
    invoice_date = fields.Date(
        string='Fecha de Factura',
        readonly=True,
        states={'draft': [('readonly', False)]},
        index=True,
        copy=False,
        default=_get_current_date
    )

    standard_id = fields.Many2one(related='inscripcion_id.standard_id', store=True)
    course_start_date = fields.Date(string='Fecha de inicio del curso')
    next_payment_date = fields.Date(string='Fecha de próxima cuota', compute='_compute_next_payment_date', inverse='_inverse_next_payment_date', store=True, readonly=False)
    fee_line_ids = fields.One2many('account.move.fee.line', 'invoice_id', string='Historial de cuotas')
    custom_payment_terms_id = fields.Many2one('account.custom.payment.terms', string='Plazos de pago')

    # OVERRIDE:
    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        if 'invoice_date_due' in vals:
            if not self.user_has_groups('account.group_account_manager'):
                raise ValidationError(_('Disculpe, debe tener el permiso de Administrador de Facturación para modificar la Fecha de vencimiento.'))
        return res

    @api.onchange('custom_payment_terms_id')
    def _onchange_custom_payment_terms_id(self):
        for rec in self:
            current_date = rec._get_current_date()
            rec.invoice_date_due = current_date
            if rec.custom_payment_terms_id and rec.custom_payment_terms_id.days:
                rec.invoice_date_due = current_date + timedelta(days=rec.custom_payment_terms_id.days)

    @api.constrains('invoice_date_due')
    def _validate_invoice_date_due(self):
        for rec in self:
            if rec.course_start_date and rec.invoice_date_due:
                if rec.invoice_date_due < rec.course_start_date:
                    raise ValidationError(_(f'La Fecha de vencimiento ({rec.invoice_date_due.strftime("%d/%m/%Y")}) no puede ser menor a la Fecha de inicio del curso ({rec.course_start_date.strftime("%d/%m/%Y")}).'))

            if rec.fee_line_ids and rec.invoice_date_due:
                last_payment_date = rec.fee_line_ids[-1].payment_date
                if rec.invoice_date_due < last_payment_date:
                    raise ValidationError(_(f'La Fecha de vencimiento ({rec.invoice_date_due.strftime("%d/%m/%Y")}) no puede ser menor a la Fecha de pago del Historial de cuotas ({last_payment_date.strftime("%d/%m/%Y")}).'))
            
    def action_register_payment(self):
        res = super().action_register_payment()
        res['context']['default_inscripcion_id'] = self.inscripcion_id.id if self.inscripcion_id else False
        res['context']['default_standard_id'] = self.standard_id.id if self.standard_id else False
        res['context']['default_payment_date'] = self.invoice_date_due
        # res['context']['invisible_concepto_pago'] = 1 if not self.inscripcion_id else 0
        # res['context']['required_concepto_pago'] = 1 if self.inscripcion_id else 0
        return res

    @api.depends(
        'fee_line_ids',
        'fee_line_ids.next_payment_date',
        'invoice_date',
        'custom_payment_terms_id',
        'custom_payment_terms_id.days'
    )
    def _compute_next_payment_date(self):
        for rec in self:
            rec.next_payment_date = False
            if rec.fee_line_ids:
                rec.next_payment_date = rec.fee_line_ids[-1].next_payment_date
            else:
                if rec.invoice_date and rec.custom_payment_terms_id:
                    rec.next_payment_date = rec.invoice_date + timedelta(days=rec.custom_payment_terms_id.days)
                    
    def _inverse_next_payment_date(self):
        for rec in self:
            if rec.fee_line_ids:
                rec.fee_line_ids[-1].next_payment_date = rec.next_payment_date        
            else:
                if rec.invoice_date and rec.custom_payment_terms_id:
                    rec.next_payment_date = rec.invoice_date + timedelta(days=rec.custom_payment_terms_id.days)

    # @api.constrains('next_payment_date', 'invoice_date_due')
    # def _check_next_payment_date(self):
    #     for rec in self:
    #         if rec.next_payment_date and rec.invoice_date_due:
    #             if rec.next_payment_date > rec.invoice_date_due:
    #                 raise ValidationError(f'La fecha de próxima cuota ({rec.next_payment_date.strftime("%d/%m/%Y")}) no puede ser mayor que la fecha de vencimiento ({rec.invoice_date_due.strftime("%d/%m/%Y")}). Puede optar por cambiar una de las dos fechas o el Plazo de pago.')