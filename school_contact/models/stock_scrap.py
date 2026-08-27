# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    note       = fields.Char('Observaciones')
 
    