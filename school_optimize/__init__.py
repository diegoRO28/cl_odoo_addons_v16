# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID
from . import models
from . import wizard

def _school_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # ================ Billing -> Asesor ================ #
    group_account_invoice_id = env.ref("account.group_account_invoice")
    group_account_invoice = env['res.groups'].search([('id', '=', group_account_invoice_id.id)])
    group_account_invoice.write({
        'name': 'Asesor'
    })
    
    # ================ Billing -> Asesor ================ #
    group_account_manager_id = env.ref("account.group_account_manager")
    group_account_manager = env['res.groups'].search([('id', '=', group_account_manager_id.id)])
    group_account_manager.write({
        'name': 'Administrador'
    })