# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_zelle = fields.Boolean(string='Zelle')
    is_pago_movil = fields.Boolean(string='Pago Móvil')

    @api.constrains('is_zelle')
    def _validate_is_zelle(self):
        for rec in self:
            zelle_records_per_company = self.search([
                ('id', '!=', rec.id),
                ('company_id', '=', rec.company_id.id),
                ('is_zelle', '=', True)
            ])
            if zelle_records_per_company:
                raise ValidationError(f'Ya existe un diario de tipo Zelle para la compañía {rec.company_id.name}.')

    @api.constrains('is_pago_movil')
    def _validate_is_pago_movil(self):
        for rec in self:
            pago_movil_records_per_company = self.search([
                ('id', '!=', rec.id),
                ('company_id', '=', rec.company_id.id),
                ('is_pago_movil', '=', True)
            ])
            if pago_movil_records_per_company:
                raise ValidationError(f'Ya existe un diario de tipo Pago Móvil para la compañía {rec.company_id.name}.')

    @api.onchange('is_zelle', 'is_pago_movil')
    def _onchange_is_zelle_pago_movil(self):
        for rec in self:
            if rec.is_zelle:
                rec.is_pago_movil = False
            elif rec.is_pago_movil:
                rec.is_zelle = False                