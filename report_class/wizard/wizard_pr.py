# -*- coding: utf-8 -*-

from datetime import timedelta
from email.policy import default
from odoo import api, fields, models
from odoo.exceptions import UserError
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
        last_day = calendar.monthrange(year, month)[1]
        return datetime.date(year,month,last_day)
    
#-----------------------------------------------------------------------#
    def get_escala(self):
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

        # CRUCIAL: Usar sudo() y with_context(active_test=False) para todo
        stuObj = self.env['student.student'].sudo().with_context(active_test=False).search([('id','=', self.student_id.id)] , order ='name asc')
        
        if not stuObj:
            raise UserError('No se encontró el estudiante seleccionado.')

        riObj = self.env['student.inscripcion'].sudo().with_context(active_test=False).search([('id','=', self.inscripcion_id.id)] , order ='name asc')
        
        if not riObj:
            raise UserError('No se encontró la inscripción seleccionada.')

        signer = self.env['cei.signer'].sudo().with_context(active_test=False).search([('id','=', self.signer_id.id)])

        # Obtener datos del estudiante
        cedula     = stuObj.student_ci or ''
        codigo     = stuObj.student_code or ''
        nombre     = stuObj.name or ''
        
        # FORZAR active_test=False para la sección
        standard_rec = riObj.standard_id.sudo().with_context(active_test=False) if riObj.standard_id else None
        
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
        
        # Procesar evaluaciones y asistencias SOLO si hay sección
        if standard_rec:
            
            # Obtener registros de evaluación con active_test=False
            registros_eva = standard_rec.registroeva_ids.sudo().with_context(active_test=False)
            registros_asi = standard_rec.asistencia_ids.sudo().with_context(active_test=False)
            
            no_eva = len(registros_eva)
            no_asi = len(registros_asi)

            #-----------------------------------------------------------------------#
            # CICLO EVALUACIONES DE LA SECCION                                      #
            #-----------------------------------------------------------------------#
            for registro_eva in registros_eva:
                if registro_eva.state == 'terminate':
                    
                    # Obtener detalles de evaluación con active_test=False
                    evaluaciones = registro_eva.evaluacion_ids.sudo().with_context(active_test=False)
                    
                    for evaluacion in evaluaciones:
                        if evaluacion.student_id.id == stuObj.id:
                            
                            contaEva += 1
                            
                            nombreEva = evaluacion.evaluacion_id.nombre if evaluacion.evaluacion_id else ''
                            notaT = evaluacion.nota if evaluacion.nota else 0.0
                            nombreSta = evaluacion.state if evaluacion.state else ''
                            acumEva += notaT
                            
                            # Obtener actividades con active_test=False
                            actividades = evaluacion.actividad_ids.sudo().with_context(active_test=False)
                            act_list = []
                            
                            for actividad in actividades:
                                act_list.append({      
                                    'nombreAct' : (actividad.nombre or '').upper(),       
                                    'nota'      : actividad.nota or 0.0,
                                    'nota_r'    : actividad.nota_r or 0.0,  
                                })
                            
                            eva.append({      
                                'nombreEva' : (nombreEva or '').upper(),       
                                'nota'      : notaT,
                                'nombreSta' : (nombreSta or '').upper(),  
                                'noAct'     : len(act_list), 
                                'listAct'   : act_list,
                            })
            
            #-----------------------------------------------------------------------#
            # CICLO ASISTENCIA DE LA SECCION                                        #
            #-----------------------------------------------------------------------#
            for registro_asi in registros_asi:
                if registro_asi.state == 'terminate':
                    
                    # Obtener detalles de asistencia con active_test=False
                    asistencias = registro_asi.asistencia_ids.sudo().with_context(active_test=False)
                    
                    for asistencia in asistencias:
                        if asistencia.student_id.id == stuObj.id:
                            contaAsi += 1
                            
                            nombreAsi = asistencia.asistencia_id.name if asistencia.asistencia_id else ''
                            nombreSta = self.get_estado(asistencia.asistencia_id.state) if asistencia.asistencia_id else ''
                            
                            if asistencia.is_attended:
                                contaAsiste += 1
                                is_asistio = 'ASISTENTE'
                            else:
                                is_asistio = 'INASISTENTE'
                            
                            asi.append({      
                                'nombreAsi' : nombreAsi, 
                                'nombreSta' : nombreSta, 
                                'is_asistio': is_asistio, 
                            })
        
        # Calcular promedios
        nombreSta = ''
        promeT = 0.0
        if contaEva != 0:
            promeT = acumEva / contaEva
            if promeT >= calificaVals.get('aprobado', 18):
                nombreSta = "APROBADO"
            else:
                nombreSta = "APLAZADO"
        
        if contaAsi != 0:
            promeA = (contaAsiste / contaAsi) * 100
        else:
            promeA = 0

        pro.append({      
            'promeT'    : promeT,
            'promeA'    : promeA,
            'nombreSta' : nombreSta,
        })
        
        # Asegurar que los datos estén completos
        data = {
            'form_data': form_data,
            'est'   : est,
            'eva'   : eva,
            'act'   : act,
            'asi'   : asi,
            'pro'   : pro,
            'signer': signer.id if signer else False,
        }

        # Forzar el contexto active_test=False en la acción del reporte
        return self.env.ref('report_class.action_report_record_pr').with_context(active_test=False).report_action(self, data=data)