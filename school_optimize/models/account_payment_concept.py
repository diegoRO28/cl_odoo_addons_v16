# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class AccountPaymentConcept(models.Model):
    _name = "account.payment.concept"

    name = fields.Char(string='Nombre')