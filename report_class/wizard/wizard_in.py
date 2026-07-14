# -*- coding: utf-8 -*-

from email.policy import default
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import calendar, datetime
from datetime import datetime

class Wizard(models.TransientModel):
    _name = 'report.wizard_in'
    _description = 'Report Wizard Facturas/Inscripcion'

    date_today      = fields.Date('Fecha Informe', default=fields.Date.today )
    date_start      = fields.Date('Fecha Inicio', required=True, default=fields.Date.today )
    date_end        = fields.Date('Fecha Fin', required=True, default=fields.Date.today)
    
    def primer_dia_mes(self):
        now = datetime.datetime.now()
        year = now.year
        month = now.month

        return datetime.date(year,month,1)

    def ultimo_dia_mes(self):
        now = datetime.datetime.now()
        year = now.year
        month = now.month
        last_day = calendar.monthrange(year, month)[1] ## último día

        return datetime.date(year,month,last_day)
    
#-----------------------------------------------------------------------#
    def action_search_salida(self):
        form_data = self.read()[0]

        move     = []
        prod     = []
     
        no_move  = 0
        j        = 1
        

        move_obj = self.env['account.move'].search([('move_type','in',['out_invoice']),('state','in',['posted'])] , order ='invoice_date')
     
        #raise ValidationError("no_student:" + str(no_ina))
        if move_obj: 

           #line_move = move_obj.filtered(lambda x: x.invoice_date >= self.date_start and x.invoice_date <= self.date_end and x.state in ['posted']) 
           #line_move = move_obj.filtered(lambda x: x.invoice_date >= self.date_start and x.state in ['posted']) 
           
           line_move  = move_obj
           
           no_move   = len(line_move)
           #raise ValidationError("no_student:" + str(no_ina))
           j       = 1
           i       = 1
           while j <= no_move:
               
               if line_move[j-1].invoice_date >= self.date_start and line_move[j-1].invoice_date <= self.date_end:
                    
                    fechaMove  = line_move[j-1].invoice_date
                    nroMove    = line_move[j-1].name
                    nombreStu  = line_move[j-1].partner_id.student_id.name
                    codeStu    = line_move[j-1].partner_id.student_code
                    montoMove  = line_move[j-1].amount_total
                    deudaMove  = line_move[j-1].amount_residual
                    stateMove  = line_move[j-1].state
                    narraMove  = line_move[j-1].narration

                    prod     = []
                    i        = 1
                    no_prod  = len(line_move[j-1].invoice_line_ids)
                    prodMove = line_move[j-1].invoice_line_ids

                    while i <= no_prod:
                        nameProd = prodMove[i-1].product_id.name
                        prod.append({       
                                    'nameProd' : nameProd,
                                   })
                        i+=1

                    move.append({       
                                    'fechaMove' : fechaMove,
                                    'nroMove'   : nroMove,
                                    'nombreStu' : nombreStu, 
                                    'codeStu'   : codeStu, 
                                    'montoMove' : montoMove, 
                                    'deudaMove' : deudaMove, 
                                    'stateMove' : stateMove,
                                    'narraMove' : narraMove,
                                    'prod'      : prod,
                                            
                                    #'company': self.env.user.company_id
                                })
                    
                                
               j = j + 1
        
        data = {
            'form_data': form_data,
            'move'     : move,

        }

        return self.env.ref('report_class.action_report_informe_inscrip').report_action(self, data=data)