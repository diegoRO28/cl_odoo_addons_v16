# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class SaleOrder(models.Model):

    _inherit = "sale.order"

    student_id = fields.Many2one(related='partner_id.student_id', store=True)
    student_code_related = fields.Char(related='student_id.student_code', store=True)
    standard_id = fields.Many2one('school.standard', compute='_compute_standard_id', store=True)

    @api.depends(
        'order_line',
        'order_line.invoice_lines',
        'order_line.invoice_lines.move_id',
        'order_line.invoice_lines.move_id.move_type',
        'order_line.invoice_lines.move_id.state',
        'order_line.invoice_lines.move_id.standard_id',
    )
    def _compute_standard_id(self):
        for order in self:
            rec.standard_id = False
            invoices = order.order_line.invoice_lines.move_id.filtered(lambda r: 
                r.move_type in ('out_invoice', 'out_refund') and
                r.state in ('draft', 'posted') and 
                r.standard_id
            )
            if invoices:
                standard_id = invoices.mapped('standard_id')
                rec.standard_id = standard_id[0].id