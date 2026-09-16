# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ResPartner(models.Model):

    _inherit = "res.partner"

    # def name_get(self):
    #     result = []
    #     for rec in self:
    #         name = f'{rec.name}'
    #         if rec.student_id:
    #             name = f'{rec.name} - {rec.student_id.student_code}' if rec.student_id.student_code else rec.name
    #         result.append((rec.id, name))
    #     return result