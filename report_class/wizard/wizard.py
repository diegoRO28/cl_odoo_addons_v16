# -*- coding: utf-8 -*-

from email.policy import default
from odoo import api, fields, models
import calendar, datetime

class Wizard(models.TransientModel):
    _name = 'report.wizard'
    _description = 'Report Wizard'

    date_start      = fields.Date('Fecha Inicio', required=True, default=fields.Date.today )
    date_end        = fields.Date('Fecha Fin', required=True, default=fields.Date.today)
    student_id      = fields.Many2one('student.student', string="Estudiante", required=True)
    inscripcion_id  = fields.Many2one('student.inscripcion', 'Secciòn', help='Selecione la secciòn', required=True)

    standard_id      = fields.Many2one('school.standard', 'Sección', related='inscripcion_id.standard_id', help='Select student standard', required=True, readonly=True)
    school_id        = fields.Many2one('school.campus', 'Campus', related='inscripcion_id.school_id', help='Select Campus', required=True, readonly=True)
    subject_id       = fields.Many2one('subject.subject', 'Curso', related='inscripcion_id.subject_id', required=True, help='Curso', readonly=True)
    start_date       = fields.Date('Fecha de inicio', required=True, related='standard_id.start_date', help='Starting date of Lapso Académico',readonly=True)
    end_date         = fields.Date('Fecha de finalización', required=True, related='standard_id.end_date', help='End date of Lapso Académico',readonly=True)
    state_sec        = fields.Selection([('por iniciar', 'Por iniciar'), 
                                         ('iniciado', 'Iniciado'),
                                         ('culminado', 'Culminado'), 
                                        ], 'Status', readonly=True, default="por iniciar", help='State of the student registration form',
                                        related='standard_id.state_aux'
                                        )


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
    def get_estado_estudiante(self , sta):
        '''Method to compute estado del estudiante en la sección.'''

        if sta == 'draft':
           return 'POR INICIAR'
        elif sta == 'done':
           return 'INSCRITO' 
        elif sta == 'terminate':
           return 'CULMINADO'
        elif sta == 'cancel':
           return 'RETIRADO'
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

        if stuObj: 
            
             cedula     = stuObj.student_ci
             codigo     = stuObj.student_code
             nombre     = stuObj.name
             seccion    = riObj.standard_id.code +  '-' + riObj.standard_id.name
             curso      = riObj.standard_id.subject_id.nombre
             estado     = self.get_estado_estudiante(riObj.state)

             est.append({      
                            'cedula'        : cedula,  
                            'codigo'        : codigo, 
                            'nombre'        : nombre, 
                            'seccion'       : seccion,
                            'curso'         : curso,
                            'estado'        : estado,
                      
                            #'company': self.env.user.company_id
                          })
             
             if riObj:
                 
                 # IMPORTANTE: forzamos active_test=False explícitamente
                 # sobre la sección (standard_id), porque acceder a los
                 # One2many registroeva_ids / asistencia_ids dispara una
                 # búsqueda nueva que, si la sección está archivada,
                 # puede devolver vacío sin este contexto.
                 standard_rec = riObj.standard_id.with_context(active_test=False)

                 seccion     = standard_rec.name
                 arreEva     = standard_rec.registroeva_ids
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
                            # Verificar que el estudiante existe en esta evaluación
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
                                    nota = raObj[i-1].nota if raObj[i-1].nota else 0.0
                                    nota_r = raObj[i-1].nota_r if raObj[i-1].nota_r else 0.0
                                
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
                        encuentro_nombre = ''
                        descripcion = ''
                        is_asistio = False
                        nombreSta = ''
                        
                        while r <= no_detalle_asi:
                            if raObj[r-1].student_id.id == stuObj.id:
                                contaAsi = contaAsi + 1
                                # Acceder a los campos con valores por defecto si son None
                                nombreAsi = raObj.asistencia_id.name if raObj.asistencia_id else ''
                                encuentro_nombre = raObj.asistencia_id.encuentro_id.name if raObj.asistencia_id and raObj.asistencia_id.encuentro_id else ''
                                descripcion = raObj.asistencia_id.note if raObj.asistencia_id and raObj.asistencia_id.note else ''
                                nombreSta = self.get_estado(raObj.asistencia_id.state) if raObj.asistencia_id else ''
                                
                                if raObj[r-1].is_attended:
                                    contaAsiste = contaAsiste + 1
                                    is_asistio = 'ASISTENTE'
                                else:
                                    is_asistio = 'INASISTENTE'
                             
                            r = r + 1
                       
                        asi.append({
                            'nombreAsi': nombreAsi,
                            'encuentro_nombre': encuentro_nombre,
                            'descripcion': descripcion,
                            'nombreSta': nombreSta,
                            'is_asistio': is_asistio,
                        })
                        
                    j = j + 1
        
        # OBTENER CALIFICACIÓN Y VALORACIÓN DIRECTAMENTE DEL MODELO student.inscripcion
        nombreSta = ''
        promeT = riObj.nota if riObj and riObj.nota else 0.0
        nombreSta = self.get_estado(riObj.state_eva) if riObj and riObj.state_eva else ''
                
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
            'pro'   : pro
        }

        return self.env.ref('report_class.action_report_record').report_action(self, data=data)