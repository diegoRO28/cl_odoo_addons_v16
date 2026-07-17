# report_class/wizard.py
# -*- coding: utf-8 -*-

from email.policy import default
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import calendar, datetime

class Wizard(models.TransientModel):
    _name = 'report.wizard'
    _description = 'Report Wizard'

    date_start = fields.Date('Fecha Inicio', required=True, default=fields.Date.today)
    date_end = fields.Date('Fecha Fin', required=True, default=fields.Date.today)
    student_id = fields.Many2one('student.student', string="Estudiante", required=True)
    inscripcion_id = fields.Many2one('student.inscripcion', 'Sección', help='Seleccione la sección', required=True)

    standard_id = fields.Many2one(
        'school.standard', 'Sección',
        related='inscripcion_id.standard_id',
        help='Select student standard',
        required=True, readonly=True
    )
    school_id = fields.Many2one(
        'school.campus', 'Campus',
        related='inscripcion_id.school_id',
        help='Select Campus',
        required=True, readonly=True
    )
    subject_id = fields.Many2one(
        'subject.subject', 'Curso',
        related='inscripcion_id.subject_id',
        required=True, help='Curso', readonly=True
    )
    start_date = fields.Date(
        'Fecha de inicio', required=True,
        related='standard_id.start_date',
        help='Starting date of Lapso Académico', readonly=True
    )
    end_date = fields.Date(
        'Fecha de finalización', required=True,
        related='standard_id.end_date',
        help='End date of Lapso Académico', readonly=True
    )
    state_sec = fields.Selection(
        [('por iniciar', 'Por iniciar'),
         ('iniciado', 'Iniciado'),
         ('culminado', 'Culminado')],
        'Status', readonly=True, default="por iniciar",
        help='State of the student registration form',
        related='standard_id.state_aux'
    )

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

    #-----------------------------------------------------------------------#
    def get_escala(self):
        """Method to compute la escala minima con soporte para custom_grade"""
        # Usar el mixin para obtener la escala
        return self.env['grade.mixin'].sudo().get_escala_custom(self.standard_id)

    #-----------------------------------------------------------------------#
    def get_estado(self, sta):
        """Method to compute la escala minima."""
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
    def get_estado_estudiante(self, sta):
        """Method to compute estado del estudiante en la sección."""
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

        est = []
        eva = []
        act = []
        asi = []
        pro = []

        no_eva = 0
        i = 1
        j = 1
        r = 1

        acumOralStu = 0
        acumEscStu = 0
        acumEva = 0
        contaEva = 0
        contaAsi = 0
        contaAsiste = 0

        promeO = 0
        promeE = 0
        promeT = 0
        promeA = 0

        calificaVals = self.get_escala()

        # Incluir registros archivados (active=False) en la búsqueda
        stuObj = self.env['student.student'].with_context(
            active_test=False
        ).search([('id', '=', self.student_id.id)], order='name asc')

        riObj = self.env['student.inscripcion'].with_context(
            active_test=False
        ).search([('id', '=', self.inscripcion_id.id)], order='name asc')

        if stuObj:
            cedula = stuObj.student_ci
            codigo = stuObj.student_code
            nombre = stuObj.name
            seccion = riObj.standard_id.code + '-' + riObj.standard_id.name
            curso = riObj.standard_id.subject_id.nombre
            estado = self.get_estado_estudiante(riObj.state)

            est.append({
                'cedula': cedula,
                'codigo': codigo,
                'nombre': nombre,
                'seccion': seccion,
                'curso': curso,
                'estado': estado,
            })

            if riObj:
                seccion = riObj.standard_id.name
                arreEva = riObj.standard_id.registroeva_ids
                no_eva = len(riObj.standard_id.registroeva_ids)
                no_asi = len(riObj.standard_id.asistencia_ids)

                #-----------------------------------------------------------------------#
                # CICLO EVALUACIONES DE LA SECCION                                      #
                #-----------------------------------------------------------------------#
                j = 1
                while j <= no_eva:
                    if riObj.standard_id.registroeva_ids[j-1].state == 'terminate':
                        reObj = riObj.standard_id.registroeva_ids[j-1].evaluacion_ids
                        no_evas = len(reObj)

                        r = 1
                        while r <= no_evas:
                            if stuObj.id == reObj[r-1].student_id.id:
                                contaEva = contaEva + 1
                                nombreEva = reObj[r-1].evaluacion_id.nombre
                                notaT = reObj[r-1].nota
                                nombreSta = reObj[r-1].state
                                acumEva += notaT

                                raObj = reObj[r-1].actividad_ids
                                no_act = len(raObj)
                                act = []
                                i = 1
                                while i <= no_act:
                                    nombreAct = raObj[i-1].nombre
                                    nota = raObj[i-1].nota
                                    nota_r = raObj[i-1].nota_r
                                    act.append({
                                        'nombreAct': nombreAct.upper(),
                                        'nota': nota,
                                        'nota_r': nota_r,
                                    })
                                    i = i + 1

                            r = r + 1

                        eva.append({
                            'nombreEva': nombreEva.upper(),
                            'nota': notaT,
                            'nombreSta': nombreSta.upper(),
                            'noAct': no_act,
                            'listAct': act,
                        })

                    j = j + 1

                #-----------------------------------------------------------------------#
                # CICLO ASISTENCIA DE LA SECCION                                        #
                #-----------------------------------------------------------------------#
                j = 1
                while j <= no_asi:
                    if riObj.standard_id.asistencia_ids[j-1].state == 'terminate':
                        raObj = riObj.standard_id.asistencia_ids[j-1].asistencia_ids
                        no_detalle_asi = len(raObj)

                        r = 1
                        nombreAsi = ''
                        encuentro_nombre = ''
                        descripcion = ''
                        is_asistio = False

                        while r <= no_detalle_asi:
                            if stuObj.id == raObj[r-1].student_id.id:
                                contaAsi = contaAsi + 1
                                nombreAsi = raObj.asistencia_id.name
                                encuentro_nombre = raObj.asistencia_id.encuentro_id.name if raObj.asistencia_id.encuentro_id else ''
                                descripcion = raObj.asistencia_id.note if raObj.asistencia_id.note else ''
                                nombreSta = self.get_estado(raObj.asistencia_id.state)

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
        promeT = riObj.nota if riObj else 0
        nombreSta = self.get_estado(riObj.state_eva) if riObj and riObj.state_eva else ''

        if contaAsi != 0:
            promeA = (contaAsiste / contaAsi) * 100

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

        return self.env.ref('report_class.action_report_record').report_action(self, data=data)