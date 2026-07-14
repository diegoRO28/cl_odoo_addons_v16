# -*- coding: utf-8 -*-

from email.policy import default
from odoo import api, fields, models
import calendar, datetime

class Wizard(models.TransientModel):
    _name = 'report.wizard_fi'
    _description = 'Report Wizard / Constancia de Estudios'

    date_start      = fields.Date('Fecha Inicio', required=True, default=fields.Date.today )
    date_end        = fields.Date('Fecha Fin', required=True, default=fields.Date.today)
    student_id      = fields.Many2one('student.student', string="Estudiante", required=True)
    # inscripcion_id  = fields.Many2one('student.inscripcion', 'Secciòn', help='Selecione la secciòn', required=True)
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
        cur    = []
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

        # Incluir registros archivados (active=True y active=False)
        stuObj = self.env['student.student'].with_context(active_test=False).search([('id','=', self.student_id.id)] , order ='name asc')

        # Incluir inscripciones archivadas y activas
        riObj = self.env['student.inscripcion'].with_context(active_test=False).search([('student_id','=', self.student_id.id),('state','in', ['done', 'terminate'])] , order ='name asc')

        signer = self.env['cei.signer'].sudo().search([('id','=', self.signer_id.id)])

        if stuObj: 
            
             cedula     = stuObj.student_ci
             codigo     = stuObj.student_code
             nombre     = stuObj.name
             
             # Usar el primer registro de inscripción para datos generales
             # O puedes dejarlo vacío si no hay inscripciones
             seccion = ''
             curso = ''
             schedule = ''
             signature = False
             director = ''
             director_id = ''
             director_job = ''
             empresa = ''
             programa = ''
             estado = ''
             
             if riObj:
                 # Tomar datos de la primera inscripción para información general
                 first_inscripcion = riObj[0]
                 
                 if first_inscripcion.standard_id.code:
                    seccion += first_inscripcion.standard_id.code
                 if first_inscripcion.standard_id.name:
                    seccion += '-' + first_inscripcion.standard_id.name
                 
                 curso      = first_inscripcion.standard_id.subject_id.nombre if first_inscripcion.standard_id.subject_id else ''
                 schedule   = first_inscripcion.standard_id.note if first_inscripcion.standard_id.note else ''
                 signature  = first_inscripcion.standard_id.company_id.director_signature if first_inscripcion.standard_id.company_id else False
                 director   = first_inscripcion.standard_id.company_id.director_name if first_inscripcion.standard_id.company_id else ''
                 director_id = first_inscripcion.standard_id.company_id.director_id if first_inscripcion.standard_id.company_id else ''
                 director_job = first_inscripcion.standard_id.company_id.director_job if first_inscripcion.standard_id.company_id else ''
                 empresa    = first_inscripcion.standard_id.company_id.name if first_inscripcion.standard_id.company_id else ''
                 programa   = first_inscripcion.standard_id.subject_id.programa_id.name if first_inscripcion.standard_id.subject_id and first_inscripcion.standard_id.subject_id.programa_id else ''
                 estado     = self.get_estado(first_inscripcion.state)

             est.append({      
                            'cedula'        : cedula,  
                            'codigo'        : codigo, 
                            'nombre'        : nombre, 
                            'seccion'       : seccion,
                            'curso'         : curso,
                            'schedule'      : schedule,
                            'signature'     : signature,
                            'director'      : director,
                            'director_id'   : director_id,
                            'director_job'  : director_job,
                            'empresa'       : empresa,
                            'programa'      : programa,
                            'estado'        : estado,
                      
                          })

             
             if riObj:
                 
                 no_cur      = len(riObj)
                 

                #-----------------------------------------------------------------------#
                # CICLO CURSOS - Iterar sobre todas las inscripciones                   #
                #-----------------------------------------------------------------------#
                 j       = 1
                 while j <= no_cur:
                    # Recalcular notas si están en 0 o en estado borrador
                    if riObj[j-1].standard_id and (riObj[j-1].nota == 0 or riObj[j-1].state_eva == 'borrador'):
                        try:
                            # Ejecutar método set_avance para recalcular promedios
                            riObj[j-1].standard_id.with_context(active_test=False).set_avance()
                        except Exception as e:
                            # Si hay error, continuar sin detener el proceso
                            pass
                    
                    curso     = riObj[j-1].subject_id.nombre if riObj[j-1].subject_id else ''
                    
                    # MODIFICACIÓN: Extraer solo la parte antes del primer slash si existe
                    seccion_completa = riObj[j-1].standard_id.code if riObj[j-1].standard_id and riObj[j-1].standard_id.code else ''
                    # Si contiene '/', tomar solo la primera parte; si no, usar el código completo
                    if seccion_completa and '/' in seccion_completa:
                        seccion = seccion_completa.split('/')[0].strip()
                    else:
                        seccion = seccion_completa
                    
                    nota      = riObj[j-1].nota
                    status    = riObj[j-1].state_eva if riObj[j-1].state_eva else ''
                  
                    cur.append({      
                                'curso'    : curso, 
                                'seccion'  : seccion, 
                                'nota'     : nota,
                                'status'   : status

                                })
                        
                    j = j + 1
                        
         
        data = {
            'form_data': form_data,
            'est'   : est,
            'cur'   : cur,
            'signer': signer.id if signer else False,
        }

        return self.env.ref('report_class.action_report_record_fi').report_action(self, data=data)