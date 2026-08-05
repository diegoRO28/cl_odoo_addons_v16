# -*- coding: utf-8 -*-

from datetime import timedelta
from email.policy import default
from odoo import api, fields, models
import calendar, datetime

class Wizard(models.TransientModel):
    _name = 'report.wizard_pr'
    _description = 'Report Wizard / Constancia de Presentación'

    date_start      = fields.Date('Fecha Inicio', required=True, default=fields.Date.today )
    date_end        = fields.Datetime('Fecha Presentación', required=True, default=fields.Datetime.now())
    student_id      = fields.Many2one('student.student', string="Estudiante", required=True)
    inscripcion_id  = fields.Many2one('student.inscripcion', 'Sección', help='Seleccione la sección', required=True)
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

        # Incluir registros archivados (active=False) en la búsqueda
        stuObj = self.env['student.student'].with_context(active_test=False).search([('id','=', self.student_id.id)] , order ='name asc')

        riObj = self.env['student.inscripcion'].with_context(active_test=False).search([('id','=', self.inscripcion_id.id)] , order ='name asc')

        signer = self.env['cei.signer'].sudo().search([('id','=', self.signer_id.id)])

        if stuObj: 
            
             cedula     = stuObj.student_ci
             codigo     = stuObj.student_code
             nombre     = stuObj.name
             
             # FORZAR active_test=False para la sección (standard_id)
             standard_rec = riObj.standard_id.with_context(active_test=False) if riObj.standard_id else None
             
             seccion    = ''
             curso      = ''
             schedule   = ''
             signature  = False
             director   = ''
             estado     = ''
             
             if standard_rec:
                 seccion    = standard_rec.code + '-' + standard_rec.name if standard_rec.code and standard_rec.name else standard_rec.name or ''
                 curso      = standard_rec.subject_id.nombre if standard_rec.subject_id else ''
                 schedule   = standard_rec.note if standard_rec.note else ''
                 signature  = standard_rec.company_id.director_signature if standard_rec.company_id else False
                 director   = standard_rec.company_id.director_name if standard_rec.company_id else ''
                 estado     = self.get_estado(riObj.state) if riObj else ''

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
             
             if standard_rec:
                 
                 seccion     = standard_rec.name
                 no_eva      = len(standard_rec.registroeva_ids)
                 no_asi      = len(standard_rec.asistencia_ids)

                #-----------------------------------------------------------------------#
                # CICLO EVALUACIONES DE LA SECCION                                      #
                #-----------------------------------------------------------------------#
                 j       = 1
                 while j <= no_eva:
                        
                    if standard_rec.registroeva_ids[j-1].state == 'terminate':
                        
                        # FORZAR active_test=False para los detalles de evaluación
                        reObj = standard_rec.registroeva_ids[j-1].with_context(active_test=False).evaluacion_ids
                        no_evas = len(reObj)
                        
                        #-----------------------------------------------------------------------#
                        # CICLO DETALLES DE EVALUACIONES DE LA SECCION                          #
                        #-----------------------------------------------------------------------#

                        r = 1
                        nombreEva = ''
                        notaT = 0.0
                        nombreSta = ''
                        
                        while r <= no_evas:
                            if reObj[r-1].student_id.id == stuObj.id:

                                contaEva = contaEva + 1

                                nombreEva = reObj[r-1].evaluacion_id.nombre if reObj[r-1].evaluacion_id else ''
                                notaT     = reObj[r-1].nota if reObj[r-1].nota else 0.0
                                nombreSta = reObj[r-1].state if reObj[r-1].state else ''
                                acumEva  += notaT
                                
                                # FORZAR active_test=False para las actividades
                                raObj = reObj[r-1].with_context(active_test=False).actividad_ids
                                no_act = len(raObj)
                                act = []
                                i = 1

                                while i <= no_act:
                                    nombreAct = raObj[i-1].nombre if raObj[i-1].nombre else ''
                                    nota      = raObj[i-1].nota if raObj[i-1].nota else 0.0
                                    nota_r    = raObj[i-1].nota_r if raObj[i-1].nota_r else 0.0
                                
                                    act.append({      
                                        'nombreAct' : nombreAct.upper(),       
                                        'nota'      : nota,
                                        'nota_r'    : nota_r,  
                                    })

                                    i = i + 1

                            
                            r = r + 1
                        
                        eva.append({      
                                    'nombreEva' : nombreEva.upper(),       
                                    'nota'      : notaT,
                                    'nombreSta' : nombreSta.upper(),  
                                    'noAct'     : no_act, 
                                    'listAct'   : act,
                                   })

                    j = j + 1
                        
                #-----------------------------------------------------------------------#
                # CICLO ASISTENCIA DE LA SECCION                                        #
                #-----------------------------------------------------------------------#
                 j       = 1
                 while j <= no_asi:
                        
                    if standard_rec.asistencia_ids[j-1].state == 'terminate':
                        
                        # FORZAR active_test=False para los detalles de asistencia
                        raObj = standard_rec.asistencia_ids[j-1].with_context(active_test=False).asistencia_ids
                        no_detalle_asi = len(raObj)

                        #-----------------------------------------------------------------------#
                        # CICLO DETALLES DE ASISTENCIA DE LA SECCION                            #
                        #-----------------------------------------------------------------------#

                        r = 1
                        nombreAsi = ''
                        is_asistio = False
                        nombreSta = ''
                        
                        while r <= no_detalle_asi:
                            if raObj[r-1].student_id.id == stuObj.id:
                                contaAsi = contaAsi + 1
                                nombreAsi = raObj.asistencia_id.name if raObj.asistencia_id else ''
                                nombreSta = self.get_estado(raObj.asistencia_id.state) if raObj.asistencia_id else ''
                                
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
            'signer': signer.id if signer else False,
        }

        return self.env.ref('report_class.action_report_record_pr').report_action(self, data=data)