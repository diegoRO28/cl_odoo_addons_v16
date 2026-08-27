# See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class AccountCustomPaymentTerms(models.Model):
    _name = 'account.custom.payment.terms'
    _description = 'Plazos de Pago'

    name = fields.Char(string='Nombre')
    days = fields.Integer(string='Días para el Pago',
        help="Número de días después de la fecha de factura para el vencimiento del pago.")
    active = fields.Boolean(string='Activo', default=True)
    description = fields.Html(string='Descripción')