# -*- coding: utf-8 -*-

from email.policy import default
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import calendar, datetime

class Wizard(models.TransientModel):
    _name = 'report.wizard_as'
    _description = 'Report Wizard Inasistencias'

    date_today = fields.Date('Fecha Informe', default=fields.Date.today)
    date_start = fields.Date('Fecha Inicio', required=True, default=fields.Date.today)
    date_end = fields.Date('Fecha Fin', required=True, default=fields.Date.today)

    # Campo para seleccionar la sección
    # domain permite elegir también secciones archivadas en el selector
    section_id = fields.Many2one(
        'school.standard',
        string="Sección",
        domain="[('active', 'in', [True, False])]"
    )

    # Campo para el tipo de reporte
    report_type = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'XLSX')
    ], string="Tipo de Reporte", required=True, default='pdf')

    def primer_dia_mes(self):
        now = datetime.datetime.now()
        year = now.year
        month = now.month

        return datetime.date(year, month, 1)

    def ultimo_dia_mes(self):
        now = datetime.datetime.now()
        year = now.year
        month = now.month
        last_day = calendar.monthrange(year, month)[1]  # último día

        return datetime.date(year, month, last_day)

    #-----------------------------------------------------------------------#
    def action_search_salida(self):
        form_data = self.read()[0]
        asi = []
        no_ina = 0
        j = 1

        # Filtrar asistencias según la sección y la compañía
        domain = [
            ('date_start', '>=', self.date_start),
            ('date_start', '<=', self.date_end),
            ('state', '=', 'terminate'),
            ('standard_id.company_id', '=', self.env.user.company_id.id)
        ]

        if self.section_id:
            domain.append(('standard_id', '=', self.section_id.id))

        # with_context(active_test=False): incluye asistencias cuya sección
        # (standard_id) fue archivada, para que esos estudiantes no
        # desaparezcan del reporte de inasistencias.
        asi_obj = self.env['subject.asistencias'].with_context(active_test=False).search(
            domain, order='date_start asc'
        )

        if asi_obj:
            line_ina = asi_obj.filtered(lambda x: not x.is_attended)

            no_ina = len(line_ina)
            while j <= no_ina:
                codeStu = line_ina[j-1].student_id.student_code
                nombreStu = line_ina[j-1].student_id.name
                nombreSec = line_ina[j-1].standard_id.code + "/" + line_ina[j-1].standard_id.subject_id.nombre
                nombreCam = line_ina[j-1].standard_id.school_id.name
                nombreEnc = line_ina[j-1].encuentro_id.name
                fechaEnc = line_ina[j-1].date_start
                nombreDoc = line_ina[j-1].standard_id.user_id.name  # Obtención del nombre del docente

                asi.append({
                    'codeStu': codeStu,
                    'nombreStu': nombreStu,
                    'nombreSec': nombreSec,
                    'nombreCam': nombreCam,
                    'nombreEnc': nombreEnc,
                    'fechaEnc': fechaEnc,
                    'nombreDoc': nombreDoc  # Añadiendo el nombre del docente a la lista
                })

                asi = sorted(asi, key=lambda r: r['fechaEnc'])

                j += 1

        data = {
            'form_data': form_data,
            'asi': asi,
        }

        # Modificar la acción de retorno para manejar el tipo de reporte
        if self.report_type == 'pdf':
            return self.env.ref('report_class.action_report_informe_ina').report_action(self, data=data)
        else:
            return self.env.ref('report_class.inasistencias_xlsx').report_action(self, data=data)