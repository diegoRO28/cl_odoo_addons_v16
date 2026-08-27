# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    image_1920 = fields.Image("Imagen", max_width=1920, max_height=1920)
    show_payment_image = fields.Boolean(compute='_compute_show_payment_image')
    concepto_pago = fields.Selection([
            ('inicial', 'Inicial'), 
            ('mensualidad', 'Mensualidad'),
            ('otros', 'Otros')
        ], 
        string='Concepto de pago'
    )
    account_payment_concept_id = fields.Many2one('account.payment.concept', string='Concepto de pago')
    inscripcion_id = fields.Many2one('student.inscripcion', string='RI')
    standard_id = fields.Many2one('school.standard', string='Sección')

    @api.depends(
        'journal_id',
        'journal_id.is_zelle',
        'journal_id.is_pago_movil',
    )
    def _compute_show_payment_image(self):
        for rec in self:
            rec.show_payment_image = False
            if rec.journal_id:
                if rec.journal_id.is_zelle or rec.journal_id.is_pago_movil:
                    rec.show_payment_image = True

    def _create_payments(self):
        payments = super(AccountPaymentRegister, self)._create_payments()
        for rec in payments:
            rec.image_1920 = self.image_1920 if self.image_1920 else False
            rec.account_payment_concept_id = self.account_payment_concept_id.id if self.account_payment_concept_id else False
            rec.inscripcion_id = self.inscripcion_id.id if self.inscripcion_id else False
            rec.standard_id = self.standard_id.id if self.standard_id else False

        # Registrando línea de Historial de cuota:
        invoice_ids = False
        if self._context.get('active_model') == 'account.move':
            invoice_ids = self.env['account.move'].browse(self._context.get('active_ids', []))        
            # Aplicando solamente a Factuas de Cliente:
            invoice_ids = invoice_ids.filtered(lambda x: x.move_type == 'out_invoice') if invoice_ids else False
        if invoice_ids:
            for invoice in invoice_ids:
                # next_payment_date = self.payment_date
                # if invoice.custom_payment_terms_id:
                #     next_payment_date = self.payment_date + timedelta(days=invoice.custom_payment_terms_id.days)
                invoice.fee_line_ids.create({
                    'invoice_id': invoice.id,
                    'payment_date': self.payment_date,
                    'amount': self.amount,
                    # 'next_payment_date': next_payment_date,
                })   

                # Actualizando fecha de vencimiento:
                # invoice.invoice_date_due = next_payment_date

        return payments