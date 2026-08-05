# -*- coding: utf-8 -*-

from datetime import timedelta
from email.policy import default
from odoo import api, fields, models
from odoo.exceptions import UserError
import calendar, datetime

class Wizard(models.TransientModel):
    _name = 'report.wizard_pr'
    _description = 'Report Wizard / Constancia de Presentación'

    date_start      = fields.Date('Fecha Inicio', required=True, default=fields.Date.today)
    date_end        = fields.Datetime('Fecha Presentación', required=True, default=fields.Datetime.now())
    student_id      = fields.Many2one('student.student', string="Estudiante", required=True, context={'active_test': False})
    inscripcion_id  = fields.Many2one('student.inscripcion', 'Sección', help='Seleccione la sección', required=True, context={'active_test': False})
    signer_id       = fields.Many2one('cei.signer', string='Firmante')

    def primer_dia_mes(self):
        now = datetime.datetime.now()
        year = now.year
        month = now.month
        return datetime.date(year, month, 1)

    def ultimo_dia_mes(self):
        now = datetime.datetime.now()
        year = now.year
        month = now.month
        last_day = calendar.monthrange(year, month)[1]
        return datetime.date(year, month, last_day)

    def get_escala(self):
        califica_vals = {'minimo': 0, 'maximo': 0, 'aprobado': 0}
        escalaObj = self.env['grade.line'].sudo().search([('sequence', '=', '1')], limit=1)
        if escalaObj:
            califica_vals = {
                'minimo': escalaObj.from_mark,
                'maximo': escalaObj.to_mark,
                'aprobado': escalaObj.pass_mark
            }
        return califica_vals

    def get_estado(self, sta):
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

    def action_search_salida(self):
        form_data = self.read()[0]

        est = []
        eva = []
        act = []
        asi = []
        pro = []

        acumEva = 0.0
        contaEva = 0
        contaAsi = 0
        contaAsiste = 0

        calificaVals = self.get_escala()

        # ============================================================
        # 1. Estudiante e Inscripción
        # ============================================================
        stuObj = self.env['student.student'].sudo().with_context(active_test=False).browse(self.student_id.id)
        if not stuObj.exists():
            raise UserError('No se encontró el estudiante seleccionado.')

        riObj = self.env['student.inscripcion'].sudo().with_context(active_test=False).browse(self.inscripcion_id.id)
        if not riObj.exists():
            raise UserError('No se encontró la inscripción seleccionada.')

        signer = self.env['cei.signer'].sudo().with_context(active_test=False).browse(self.signer_id.id) if self.signer_id else False

        cedula = stuObj.student_ci or ''
        codigo = stuObj.student_code or ''
        nombre = stuObj.name or ''

        # ============================================================
        # 2. Sección (incluyendo archivada)
        # ============================================================
        standard_rec = riObj.standard_id.sudo().with_context(active_test=False) if riObj.standard_id else None

        seccion = ''
        curso = ''
        schedule = ''
        signature = False
        director = ''
        estado = ''

        if standard_rec:
            seccion = (standard_rec.code + '-' + standard_rec.name) if standard_rec.code and standard_rec.name else (standard_rec.name or '')
            curso = standard_rec.subject_id.nombre if standard_rec.subject_id else ''
            schedule = standard_rec.note if standard_rec.note else ''
            signature = standard_rec.company_id.director_signature if standard_rec.company_id else False
            director = standard_rec.company_id.director_name if standard_rec.company_id else ''
            estado = self.get_estado(riObj.state) if riObj else ''

        est.append({
            'cedula': cedula,
            'codigo': codigo,
            'nombre': nombre,
            'seccion': seccion,
            'curso': curso,
            'schedule': schedule,
            'signature': signature,
            'director': director,
            'estado': estado,
        })

        if standard_rec:
            # ============================================================
            # 3. EVALUACIONES - Búsqueda CORRECTA para secciones archivadas
            # ============================================================
            # PRIMERO: Buscar TODAS las evaluaciones de la sección (incluyendo archivadas)
            evaluaciones_seccion = self.env['standard.evaluacion'].sudo().with_context(active_test=False).search([
                ('standard_id', '=', standard_rec.id),
                ('state', '=', 'terminate')
            ])
            
            # SEGUNDO: Para cada evaluación, buscar las notas del estudiante
            for eval_seccion in evaluaciones_seccion:
                evaluaciones = self.env['standard.evaluaciones'].sudo().with_context(active_test=False).search([
                    ('evaluacion_id', '=', eval_seccion.id),
                    ('student_id', '=', stuObj.id)
                ])

                for evaluacion in evaluaciones:
                    contaEva += 1
                    nombreEva = evaluacion.evaluacion_id.nombre if evaluacion.evaluacion_id else ''
                    notaT = evaluacion.nota if evaluacion.nota else 0.0
                    nombreSta = evaluacion.state if evaluacion.state else ''
                    acumEva += notaT

                    actividades = self.env['standard.actividades'].sudo().with_context(active_test=False).search([
                        ('evaluacion_id', '=', evaluacion.id)
                    ])

                    act_list = []
                    for actividad in actividades:
                        act_list.append({
                            'nombreAct': (actividad.nombre or '').upper(),
                            'nota': actividad.nota or 0.0,
                            'nota_r': actividad.nota_r or 0.0,
                        })

                    eva.append({
                        'nombreEva': (nombreEva or '').upper(),
                        'nota': notaT,
                        'nombreSta': (nombreSta or '').upper(),
                        'noAct': len(act_list),
                        'listAct': act_list,
                    })

            # ============================================================
            # 4. ASISTENCIAS - Búsqueda CORRECTA para secciones archivadas
            # ============================================================
            # PRIMERO: Buscar TODAS las asistencias de la sección (incluyendo archivadas)
            asistencias_seccion = self.env['subject.asistencia'].sudo().with_context(active_test=False).search([
                ('standard_id', '=', standard_rec.id),
                ('state', '=', 'terminate')
            ])
            
            # SEGUNDO: Para cada asistencia, buscar el registro del estudiante
            for asis_seccion in asistencias_seccion:
                asistencias = self.env['subject.asistencias'].sudo().with_context(active_test=False).search([
                    ('asistencia_id', '=', asis_seccion.id),
                    ('student_id', '=', stuObj.id)
                ])

                for asistencia in asistencias:
                    contaAsi += 1
                    nombreAsi = asistencia.asistencia_id.name if asistencia.asistencia_id else ''
                    nombreSta = self.get_estado(asistencia.asistencia_id.state) if asistencia.asistencia_id else ''

                    if asistencia.is_attended:
                        contaAsiste += 1
                        is_asistio = 'ASISTENTE'
                    else:
                        is_asistio = 'INASISTENTE'

                    asi.append({
                        'nombreAsi': nombreAsi,
                        'nombreSta': nombreSta,
                        'is_asistio': is_asistio,
                    })

        # ============================================================
        # 5. Promedios
        # ============================================================
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
            promeA = 0.0

        pro.append({
            'promeT': promeT,
            'promeA': promeA,
            'nombreSta': nombreSta,
        })

        data = {
            'form_data': form_data,
            'est': est,
            'eva': eva,
            'act': act,
            'asi': asi,
            'pro': pro,
            'signer': signer.id if signer else False,
        }

        return self.env.ref('report_class.action_report_record_pr').with_context(active_test=False).report_action(self, data=data)