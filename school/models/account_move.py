# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

#------------------------------------------------------------------------------------------------
# ACCOUNT MOVE
#------------------------------------------------------------------------------------------------

class account_move(models.Model):
    _inherit = 'account.move'
    
    is_inscripcion = fields.Boolean(string="Es RI ?", default=False)
    inscripcion_id = fields.Many2one('student.inscripcion', 'RI', help='Registro de Inscripción')
