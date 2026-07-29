# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ProductCategory(models.Model):
    _inherit = 'poduct.category'

    note       = fields.Char('Observaciones')
 
    