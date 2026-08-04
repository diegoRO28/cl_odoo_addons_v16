# -*- coding: utf-8 -*-

from datetime import timedelta
from email.policy import default
from odoo import api, fields, models
import calendar, datetime

class Wizard(models.TransientModel):
    _name = 'report.wizard_pr'
    _description = 'Report Wizard / Constancia de Estudios'

    date_start      = fields.Date('Fecha Inicio', required=True, default=fields.Date.today )
    date_end        = fields.Datetime('Fecha Presentación', required=True, default=fields.Datetime.now())
    student_id      = fields.Many2one('student.student', string="Estudiante", required=True)
    inscripcion_id  = fields.Many2one('student.inscripcion', 'Secciòn', help='Selecione la secciòn', required=True)
    signer_id       = fields.Many2one('cei.signer', string='Firmante')

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
    def get_escala(self):
        '''Method to compute la escala minima.'''

        califica_vals = {'minimo': 0, 'maximo': 0 , 'aprobado': 0 }
  
        escalaObj = self.env['grade.line'].sudo().search([('sequence', '=', '1')], limit=1)

        if escalaObj:
           califica_vals = {'minimo': escalaObj.from_mark, 
                            'maximo': escalaObj.to_mark,
                            'aprobado': escalaObj.pass_mark
                           }
        
        return califica_vals
    
#-----------------------------------------------------------------------#
    def get_estado(self , sta):
        '''Method to compute la escala minima.'''

        if sta == 'draft':
           return 'POR INICIAR'
        elif sta == 'done':
           return 'INICIADO' 
        elif sta == 'terminate':
           return 'CULMINADO'
        elif sta == 'aprobado':
           return 'APROBADO'
        elif sta == 'aplazado':
           return 'APLAZADO'
        else:
            return sta
        
        return sta
    
#-----------------------------------------------------------------------#
    def action_search_salida(self):
        form_data = self.read()[0]

        est    = []
        eva    = []
        act    = []
        asi    = []
        pro    = []

        no_eva      = 0
        i           = 1
        j           = 1
        r           = 1

        acumOralStu = 0
        acumEscStu  = 0
        acumEva     = 0
        contaEva    = 0
        contaAsi    = 0
        contaAsiste = 0

        promeO      = 0
        promeE      = 0
        promeT      = 0
        promeA      = 0

        calificaVals = self.get_escala()

        stuObj = self.env['student.student'].search([('id','=', self.student_id.id)] , order ='name asc')

        riObj = self.env['student.inscripcion'].search([('id','=', self.inscripcion_id.id)] , order ='name asc')

        signer = self.env['cei.signer'].sudo().search([('id','=', self.signer_id.id)])

        if stuObj: 
            
             cedula     = stuObj.student_ci
             codigo     = stuObj.student_code
             nombre     = stuObj.name
             seccion    = riObj.standard_id.code +  '-' + riObj.standard_id.name
             curso      = riObj.standard_id.subject_id.nombre
             schedule   = riObj.standard_id.note
             signature  = riObj.standard_id.company_id.director_signature
             director   = riObj.standard_id.company_id.director_name
             estado     = self.get_estado(riObj.state)

             est.append({      
                            'cedula'        : cedula,  
                            'codigo'        : codigo, 
                            'nombre'        : nombre, 
                            'seccion'       : seccion,
                            'curso'         : curso,
                            'schedule'      : schedule,
                            'signature'     : signature,
                            'director'      : director,
                            'estado'        : estado,
                      
                          })
             
             if riObj:
                 
                 seccion     = riObj.standard_id.name
                 arreEva     = riObj.standard_id.registroeva_ids
                 no_eva      = len(riObj.standard_id.registroeva_ids)
                 no_asi      = len(riObj.standard_id.asistencia_ids)

                #-----------------------------------------------------------------------#
                # CICLO EVALUACIONES DE LA SECCION                                      #
                #-----------------------------------------------------------------------#
                 j       = 1
                 while j <= no_eva:
                        
                    if riObj.standard_id.registroeva_ids[j-1].state == 'terminate':
                        
                        reObj   = riObj.standard_id.registroeva_ids[j-1].with_context(active_test=False).evaluacion_ids
                        no_evas = len(reObj)
                        
                        #-----------------------------------------------------------------------#
                        # CICLO DETALLES DE EVALUACIONES DE LA SECCION                          #
                        #-----------------------------------------------------------------------#

                        r = 1

                        while r <= no_evas:
                            if stuObj.id == reObj[r-1].student_id.id:

                                contaEva = contaEva + 1

                                nombreEva = reObj[r-1].evaluacion_id.nombre
                                notaT     = reObj[r-1].nota
                                nombreSta = reObj[r-1].state
                                acumEva  += notaT
                                
                                raObj     = reObj[r-1].actividad_ids
                                no_act    = len(raObj)
                                act       = []
                                i = 1

                                while i <= no_act:
                                    nombreAct = raObj[i-1].nombre
                                    nota      = raObj[i-1].nota
                                    nota_r    = raObj[i-1].nota_r
                                
                                    act.append({      
                                        'nombreAct' : nombreAct.upper(),       
                                        'nota'      : nota,
                                        'nota_r'    : nota_r,  
                                        #'company': self.env.user.company_id
                                    })

                                    i = i + 1

                            
                            r = r + 1
                        
                        eva.append({      
                                    'nombreEva' : nombreEva.upper(),       
                                    'nota'      : notaT,
                                    'nombreSta' : nombreSta.upper(),  
                                    'noAct'     : no_act, 
                                    'listAct'   : act,
                                    

                                    #'company': self.env.user.company_id
                                   })

                    j = j + 1
                        
                #-----------------------------------------------------------------------#
                # CICLO ASISTENCIA DE LA SECCION                                      #
                #-----------------------------------------------------------------------#
                 j       = 1
                 while j <= no_asi:
                        
                    if riObj.standard_id.asistencia_ids[j-1].state == 'terminate':
                        
                        raObj   = riObj.standard_id.asistencia_ids[j-1].with_context(active_test=False).asistencia_ids
                        no_detalle_asi  = len(raObj)

                        #-----------------------------------------------------------------------#
                        # CICLO DETALLES DE ASISTENCIA DE LA SECCION                          #
                        #-----------------------------------------------------------------------#

                        r = 1
                        nombreAsi = ''
                        is_asistio = False
                        while r <= no_detalle_asi:
                            if stuObj.id == raObj[r-1].student_id.id:
                                contaAsi = contaAsi + 1
                                nombreAsi  = raObj.asistencia_id.name
                                nombreSta  = self.get_estado(raObj.asistencia_id.state)
                                
                                if raObj[r-1].is_attended:
                                    contaAsiste = contaAsiste + 1
                                    is_asistio = 'ASISTENTE'
                                else:
                                    is_asistio = 'INASISTENTE'
                             
                            r = r + 1
                       
                        asi.append({      
                                    'nombreAsi' : nombreAsi, 
                                    'nombreSta' : nombreSta, 
                                    'is_asistio': is_asistio, 
                                    
                                    #'company': self.env.user.company_id
                                   })
                        
                    j = j + 1
                        
        nombreSta = ''
        if contaEva != 0:
                promeT = acumEva / contaEva

                if promeT >= calificaVals['aprobado']:
                        nombreSta = "APROBADO"
                else:
                        nombreSta = "APLAZADO"
                
        if contaAsi != 0:
            promeA = (contaAsiste/contaAsi)*100


        pro.append({      
                    'promeT'    : promeT,
                    'promeA'    : promeA,
                    'nombreSta' : nombreSta,

                   })
        
        data = {
            'form_data': form_data,
            'est'   : est,
            'eva'   : eva,
            'act'   : act,
            'asi'   : asi,
            'pro'   : pro,
            'signer': signer.id,
        }

        return self.env.ref('report_class.action_report_record_pr').report_action(self, data=data)