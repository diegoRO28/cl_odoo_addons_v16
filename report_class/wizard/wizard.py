# -*- coding: utf-8 -*-

from email.policy import default
from odoo import api, fields, models
from odoo.exceptions import UserError
import calendar, datetime

class Wizard(models.TransientModel):
    _name = 'report.wizard'
    _description = 'Report Wizard'

    date_start      = fields.Date('Fecha Inicio', required=True, default=fields.Date.today)
    date_end        = fields.Date('Fecha Fin', required=True, default=fields.Date.today)
    student_id = fields.Many2one(
        'student.student',
        string="Estudiante",
        required=True,
        context={'active_test': False}  # <--- AÑADIR ESTO
    )
    inscripcion_id = fields.Many2one(
        'student.inscripcion',
        'Sección',
        help='Seleccione la sección',
        required=True,
        context={'active_test': False}  # <--- AÑADIR ESTO
    )

    standard_id      = fields.Many2one('school.standard', 'Sección', related='inscripcion_id.standard_id', help='Select student standard', required=True, readonly=True)
    school_id        = fields.Many2one('school.campus', 'Campus', related='inscripcion_id.school_id', help='Select Campus', required=True, readonly=True)
    subject_id       = fields.Many2one('subject.subject', 'Curso', related='inscripcion_id.subject_id', required=True, help='Curso', readonly=True)
    start_date       = fields.Date('Fecha de inicio', required=True, related='standard_id.start_date', help='Starting date of Lapso Académico', readonly=True)
    end_date         = fields.Date('Fecha de finalización', required=True, related='standard_id.end_date', help='End date of Lapso Académico', readonly=True)
    state_sec        = fields.Selection([
        ('por iniciar', 'Por iniciar'),
        ('iniciado', 'Iniciado'),
        ('culminado', 'Culminado'),
    ], 'Status', readonly=True, default="por iniciar", help='State of the student registration form',
        related='standard_id.state_aux')

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
            return sta or ''
        return sta or ''

    def get_estado_estudiante(self, sta):
        if sta == 'draft':
            return 'POR INICIAR'
        elif sta == 'done':
            return 'INSCRITO'
        elif sta == 'terminate':
            return 'CULMINADO'
        elif sta == 'cancel':
            return 'RETIRADO'
        else:
            return sta or ''
        return sta or ''

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
        # 1. Estudiante e Inscripción (incluyendo archivados)
        # ============================================================
        stuObj = self.env['student.student'].sudo().with_context(active_test=False).browse(self.student_id.id)
        if not stuObj.exists():
            raise UserError('No se encontró el estudiante seleccionado.')

        riObj = self.env['student.inscripcion'].sudo().with_context(active_test=False).browse(self.inscripcion_id.id)
        if not riObj.exists():
            raise UserError('No se encontró la inscripción seleccionada.')

        cedula = stuObj.student_ci or ''
        codigo = stuObj.student_code or ''
        nombre = stuObj.name or ''

        # ============================================================
        # 2. Sección (incluyendo archivada)
        # ============================================================
        standard_rec = False
        if riObj.standard_id:
            standard_rec = self.env['school.standard'].sudo().with_context(active_test=False).browse(riObj.standard_id.id)

        seccion = ''
        curso = ''
        estado = ''

        if standard_rec and standard_rec.exists():
            seccion = (standard_rec.code + '-' + standard_rec.name) if standard_rec.code and standard_rec.name else (standard_rec.name or '')
            curso = standard_rec.subject_id.nombre if standard_rec.subject_id else ''
            estado = self.get_estado_estudiante(riObj.state) if riObj else ''

        est.append({
            'cedula': cedula,
            'codigo': codigo,
            'nombre': nombre,
            'seccion': seccion,
            'curso': curso,
            'estado': estado,
        })

        if standard_rec and standard_rec.exists():
            # ============================================================
            # 3. EVALUACIONES - Búsqueda DIRECTA por estudiante + sección
            #    (no depende del estado del maestro ni de One2many)
            # ============================================================
            evaluaciones = self.env['standard.evaluaciones'].sudo().with_context(active_test=False).search([
                ('student_id', '=', stuObj.id),
                ('evaluacion_id.standard_id', '=', standard_rec.id),
            ])

            for evaluacion in evaluaciones:
                contaEva += 1
                nombreEva = evaluacion.evaluacion_id.nombre if evaluacion.evaluacion_id else ''
                notaT = evaluacion.nota if evaluacion.nota else 0.0
                nombreSta = evaluacion.state if evaluacion.state else ''
                acumEva += notaT

                # Actividades del detalle
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
            # 4. ASISTENCIAS - Búsqueda DIRECTA por estudiante + sección
            # ============================================================
            asistencias = self.env['subject.asistencias'].sudo().with_context(active_test=False).search([
                ('student_id', '=', stuObj.id),
                ('asistencia_id.standard_id', '=', standard_rec.id),
            ])

            for asistencia in asistencias:
                contaAsi += 1

                nombreAsi = asistencia.asistencia_id.name if asistencia.asistencia_id else ''
                encuentro_nombre = ''
                if asistencia.asistencia_id and asistencia.asistencia_id.encuentro_id:
                    encuentro_nombre = asistencia.asistencia_id.encuentro_id.name or ''
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

        # ============================================================
        # 5. Promedios
        # ============================================================
        promeT = riObj.nota if riObj and riObj.nota else 0.0
        nombreSta = self.get_estado(riObj.state_eva) if riObj and riObj.state_eva else ''

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
            'pro': pro
        }

        return self.env.ref('report_class.action_report_record').with_context(active_test=False).report_action(self, data=data)