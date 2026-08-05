# -*- coding: utf-8 -*-

from email.policy import default
from odoo import api, fields, models
from odoo.exceptions import UserError
import calendar, datetime

class Wizard(models.TransientModel):
    _name = 'report.wizard_fi'
    _description = 'Report Wizard / Constancia de Finalización'

    date_start      = fields.Date('Fecha Inicio', required=True, default=fields.Date.today )
    date_end        = fields.Date('Fecha Fin', required=True, default=fields.Date.today)
    student_id      = fields.Many2one('student.student', string="Estudiante", required=True)
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

        # Incluir registros archivados
        stuObj = self.env['student.student'].sudo().with_context(active_test=False).search([('id','=', self.student_id.id)] , order ='name asc')
        
        if not stuObj:
            raise UserError('No se encontró el estudiante seleccionado.')

        # Incluir inscripciones archivadas y activas
        riObj = self.env['student.inscripcion'].sudo().with_context(active_test=False).search([('student_id','=', self.student_id.id),('state','in', ['done', 'terminate'])] , order ='name asc')

        signer = self.env['cei.signer'].sudo().with_context(active_test=False).search([('id','=', self.signer_id.id)])

        cedula     = stuObj.student_ci or ''
        codigo     = stuObj.student_code or ''
        nombre     = stuObj.name or ''
        
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
            first_inscripcion = riObj[0]
            standard_rec = first_inscripcion.standard_id.sudo().with_context(active_test=False) if first_inscripcion.standard_id else None
            
            if standard_rec:
                seccion = ''
                if standard_rec.code:
                    seccion += standard_rec.code
                if standard_rec.name:
                    seccion += '-' + standard_rec.name
                curso      = standard_rec.subject_id.nombre if standard_rec.subject_id else ''
                schedule   = standard_rec.note if standard_rec.note else ''
                signature  = standard_rec.company_id.director_signature if standard_rec.company_id else False
                director   = standard_rec.company_id.director_name if standard_rec.company_id else ''
                director_id = standard_rec.company_id.director_id if standard_rec.company_id else ''
                director_job = standard_rec.company_id.director_job if standard_rec.company_id else ''
                empresa    = standard_rec.company_id.name if standard_rec.company_id else ''
                programa   = standard_rec.subject_id.programa_id.name if standard_rec.subject_id and standard_rec.subject_id.programa_id else ''
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
            no_cur = len(riObj)
            
            for inscripcion in riObj:
                # Recalcular notas si están en 0 o en estado borrador
                if inscripcion.standard_id and (inscripcion.nota == 0 or inscripcion.state_eva == 'borrador'):
                    try:
                        inscripcion.standard_id.sudo().with_context(active_test=False).set_avance()
                    except Exception as e:
                        pass
                
                curso = inscripcion.subject_id.nombre if inscripcion.subject_id else ''
                
                seccion_completa = inscripcion.standard_id.code if inscripcion.standard_id and inscripcion.standard_id.code else ''
                if seccion_completa and '/' in seccion_completa:
                    seccion = seccion_completa.split('/')[0].strip()
                else:
                    seccion = seccion_completa
                
                nota = inscripcion.nota if inscripcion.nota else 0.0
                status = inscripcion.state_eva if inscripcion.state_eva else ''
                
                cur.append({      
                    'curso'    : curso, 
                    'seccion'  : seccion, 
                    'nota'     : nota,
                    'status'   : status
                })
        
        data = {
            'form_data': form_data,
            'est'   : est,
            'cur'   : cur,
            'signer': signer.id if signer else False,
        }

        return self.env.ref('report_class.action_report_record_fi').with_context(active_test=False).report_action(self, data=data)