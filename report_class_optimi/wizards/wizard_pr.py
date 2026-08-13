# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
import calendar
import datetime


class WizardPrOptimized(models.TransientModel):
    _name = 'report.wizard.pr.optimized'
    _description = 'Report Wizard Optimizado - Constancia de Presentación'

    # Campos del wizard
    student_id = fields.Many2one('student.student', string="Estudiante", required=True, context={'active_test': False})
    inscripcion_id = fields.Many2one('student.inscripcion', 'Sección', help='Seleccione la sección', required=True, context={'active_test': False})
    signer_id = fields.Many2one('cei.signer', string='Firmante', context={'active_test': False})
    date_end = fields.Datetime('Fecha Presentación', required=True, default=fields.Datetime.now())
    date_start = fields.Date('Fecha Inicio', required=True, default=fields.Date.today)

    def action_search_salida(self):
        """
        Método optimizado para generar la constancia de presentación
        incluyendo secciones archivadas.
        """
        form_data = self.read()[0]

        helper = self.env['report.helper.optimized']

        # Obtener estudiante e inscripción (incluye archivados)
        student = helper.get_student(self.student_id.id)
        inscripcion = helper.get_inscripcion(self.inscripcion_id.id)
        standard = helper.get_standard(inscripcion)

        # Obtener firmante
        signer = False
        if self.signer_id:
            signer = self.env['cei.signer'].sudo().with_context(active_test=False).browse(self.signer_id.id)

        # Preparar datos del estudiante
        est = [{
            'cedula': student.student_ci or '',
            'codigo': student.student_code or '',
            'nombre': student.name or '',
            'seccion': standard.code if standard else '',
            'curso': standard.subject_id.nombre if standard and standard.subject_id else '',
            'schedule': standard.note if standard else '',
            'signature': standard.company_id.director_signature if standard and standard.company_id else False,
            'director': standard.company_id.director_name if standard and standard.company_id else '',
            'estado': self.get_estado(inscripcion.state),
        }]

        data = {
            'form_data': form_data,
            'est': est,
            'signer': signer.id if signer else False,
        }

        return self.env.ref('report_class.action_report_record_pr') \
            .with_context(active_test=False) \
            .report_action(self, data=data)

    def get_estado(self, sta):
        """Mapeo de estados."""
        estados = {
            'draft': 'POR INICIAR',
            'done': 'INICIADO',
            'terminate': 'CULMINADO',
            'aprobado': 'APROBADO',
            'aplazado': 'APLAZADO',
        }
        return estados.get(sta, sta or '')