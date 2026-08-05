# -*- coding: utf-8 -*-

from email.policy import default
from odoo import api, fields, models
from odoo.exceptions import UserError
import calendar, datetime

class Wizard(models.TransientModel):
    _name = 'report.wizard'
    _description = 'Report Wizard'

    date_start      = fields.Date('Fecha Inicio', required=True, default=fields.Date.today )
    date_end        = fields.Date('Fecha Fin', required=True, default=fields.Date.today)
    student_id      = fields.Many2one('student.student', string="Estudiante", required=True)
    inscripcion_id  = fields.Many2one('student.inscripcion', 'Sección', help='Seleccione la sección', required=True)

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
    def get_estado_estudiante(self , sta):
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

        # Incluir registros archivados
        stuObj = self.env['student.student'].sudo().with_context(active_test=False).search([('id','=', self.student_id.id)] , order ='name asc')
        
        if not stuObj:
            raise UserError('No se encontró el estudiante seleccionado.')

        riObj = self.env['student.inscripcion'].sudo().with_context(active_test=False).search([('id','=', self.inscripcion_id.id)] , order ='name asc')
        
        if not riObj:
            raise UserError('No se encontró la inscripción seleccionada.')

        cedula     = stuObj.student_ci or ''
        codigo     = stuObj.student_code or ''
        nombre     = stuObj.name or ''
        
        # FORZAR active_test=False para la sección
        standard_rec = riObj.standard_id.sudo().with_context(active_test=False) if riObj.standard_id else None
        
        seccion    = ''
        curso      = ''
        estado     = ''
        
        if standard_rec:
            seccion    = standard_rec.code + '-' + standard_rec.name if standard_rec.code and standard_rec.name else standard_rec.name or ''
            curso      = standard_rec.subject_id.nombre if standard_rec.subject_id else ''
            estado     = self.get_estado_estudiante(riObj.state) if riObj else ''

        est.append({      
            'cedula'        : cedula,  
            'codigo'        : codigo, 
            'nombre'        : nombre, 
            'seccion'       : seccion,
            'curso'         : curso,
            'estado'        : estado,
        })
        
        if standard_rec:
            
            # Obtener registros con active_test=False
            registros_eva = standard_rec.registroeva_ids.sudo().with_context(active_test=False)
            registros_asi = standard_rec.asistencia_ids.sudo().with_context(active_test=False)
            
            no_eva = len(registros_eva)
            no_asi = len(registros_asi)

            #-----------------------------------------------------------------------#
            # CICLO EVALUACIONES DE LA SECCION                                      #
            #-----------------------------------------------------------------------#
            for registro_eva in registros_eva:
                if registro_eva.state == 'terminate':
                    
                    evaluaciones = registro_eva.evaluacion_ids.sudo().with_context(active_test=False)
                    
                    for evaluacion in evaluaciones:
                        if evaluacion.student_id.id == stuObj.id:
                            
                            contaEva += 1
                            
                            nombreEva = evaluacion.evaluacion_id.nombre if evaluacion.evaluacion_id else ''
                            notaT = evaluacion.nota if evaluacion.nota else 0.0
                            nombreSta = evaluacion.state if evaluacion.state else ''
                            acumEva += notaT
                            
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
                    
                    asistencias = registro_asi.asistencia_ids.sudo().with_context(active_test=False)
                    
                    for asistencia in asistencias:
                        if asistencia.student_id.id == stuObj.id:
                            contaAsi += 1
                            
                            nombreAsi = asistencia.asistencia_id.name if asistencia.asistencia_id else ''
                            encuentro_nombre = asistencia.asistencia_id.encuentro_id.name if asistencia.asistencia_id and asistencia.asistencia_id.encuentro_id else ''
                            descripcion = asistencia.asistencia_id.note if asistencia.asistencia_id and asistencia.asistencia_id.note else ''
                            nombreSta = self.get_estado(asistencia.asistencia_id.state) if asistencia.asistencia_id else ''
                            
                            if asistencia.is_attended:
                                contaAsiste += 1
                                is_asistio = 'ASISTENTE'
                            else:
                                is_asistio = 'INASISTENTE'
                            
                            asi.append({
                                'nombreAsi': nombreAsi,
                                'encuentro_nombre': encuentro_nombre,
                                'descripcion': descripcion,
                                'nombreSta': nombreSta,
                                'is_asistio': is_asistio,
                            })
        
        # Obtener calificación del modelo student.inscripcion
        nombreSta = ''
        promeT = riObj.nota if riObj and riObj.nota else 0.0
        nombreSta = self.get_estado(riObj.state_eva) if riObj and riObj.state_eva else ''
        
        if contaAsi != 0:
            promeA = (contaAsiste / contaAsi) * 100
        else:
            promeA = 0

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

        return self.env.ref('report_class.action_report_record').with_context(active_test=False).report_action(self, data=data)