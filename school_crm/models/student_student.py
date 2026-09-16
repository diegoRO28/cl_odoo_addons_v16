# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class StudentStudent(models.Model):

    _inherit = 'student.student'

    opportunity_id = fields.Many2one('crm.lead', string='Oportunidad')