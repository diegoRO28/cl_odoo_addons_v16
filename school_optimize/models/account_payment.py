# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class AccountPayment(models.Model):
    _name = "account.payment"

    _inherit = ['account.payment', 'mail.thread', 'mail.activity.mixin', 'image.mixin']

    inscripcion_id = fields.Many2one('student.inscripcion', string='RI')
    standard_id = fields.Many2one('school.standard', string='Sección') 
    concepto_pago = fields.Selection([
            ('inicial', 'Inicial'), 
            ('mensualidad', 'Mensualidad'),
            ('otros', 'Otros')
        ], 
        string='Concepto de pago'
    )        
    account_payment_concept_id = fields.Many2one('account.payment.concept', string='Concepto de pago')