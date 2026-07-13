# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class res_partner(models.Model):
    _inherit = 'res.partner'

    
    nombre = fields.Char('ID Number')

    # company_type is only an interface field, do not use it in business logic
    #company_type = fields.Selection(string='Company Type',
    #    selection=[('person', 'Individual'), ('company', 'Company'), ('student', 'Estudiante')],
    #    compute='_compute_company_type', inverse='_write_company_type') 
    
