# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class AccountMoveFeeLine(models.Model):

    _name = 'account.move.fee.line'

    invoice_id = fields.Many2one('account.move', string='Factura')
    payment_date = fields.Date(string='Fecha de Pago')
    amount = fields.Monetary(string='Monto Pagado')
    next_payment_date = fields.Date(string='Próxima Fecha de Pago')
    currency_id = fields.Many2one(related='invoice_id.currency_id')