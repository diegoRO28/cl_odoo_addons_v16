# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    director_signature = fields.Binary(string="Firma", attachment=True)
    director_name = fields.Char(string='Director', help='Escriba el nombre del director')
    director_id   = fields.Char(string='Identificación', help='Escriba la identificación')
    director_job  = fields.Char(string='Cargo', help='Escriba el cargo')
