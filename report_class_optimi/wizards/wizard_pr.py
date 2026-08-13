# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
import calendar
import datetime


class WizardPrOptimized(models.TransientModel):
    """
    Hereda de report.wizard_pr y mejora la obtención de datos
    para incluir secciones archivadas.
    """
    _name = 'report.wizard_pr'
    _inherit = 'report.wizard_pr'  # Hereda del wizard original

    def action_search_salida(self):
        """
        Sobrescribe el método original para incluir secciones archivadas.
        """
        form_data = self.read()[0]

        helper = self.env['report.helper.optimized']

        # Obtener estudiante e inscripción (incluye archivados)
        student = helper.get_student(self.student_id.id)
        inscripcion = helper.get_inscripcion(self.inscripcion_id.id)
        standard = helper.get_standard(inscripcion)

        # Obtener datos de la empresa (si existe)
        company_data = {}
        if standard and standard.company_id:
            company_data = {
                'signature': standard.company_id.director_signature or False,
                'director': standard.company_id.director_name or '',
            }

        # Preparar datos del estudiante
        est = [{
            'cedula': student.student_ci or '',
            'codigo': student.student_code or '',
            'nombre': student.name or '',
            'seccion': standard.code if standard else '',
            'curso': standard.subject_id.nombre if standard and standard.subject_id else '',
            'schedule': standard.note if standard else '',
            'signature': company_data.get('signature', False),
            'director': company_data.get('director', ''),
            'estado': self.get_estado(inscripcion.state),
        }]

        data = {
            'form_data': form_data,
            'est': est,
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