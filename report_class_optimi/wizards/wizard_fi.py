# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
import calendar
import datetime


class WizardFiOptimized(models.TransientModel):
    """
    Hereda de report.wizard_fi y mejora la obtención de datos
    para incluir secciones archivadas.
    """
    _name = 'report.wizard_fi'
    _inherit = 'report.wizard_fi'  # Hereda del wizard original

    def action_search_salida(self):
        """
        Sobrescribe el método original para incluir secciones archivadas.
        """
        form_data = self.read()[0]

        helper = self.env['report.helper.optimized']

        # Obtener estudiante (incluye archivados)
        student = helper.get_student(self.student_id.id)

        # Obtener firmante
        signer = False
        if self.signer_id:
            signer = self.env['cei.signer'].sudo().with_context(active_test=False).browse(self.signer_id.id)

        # Datos del estudiante
        est = [{
            'cedula': student.student_ci or '',
            'codigo': student.student_code or '',
            'nombre': student.name or '',
        }]

        # Obtener todas las inscripciones históricas
        inscripciones = helper.get_inscripciones_historicas(student)

        # Preparar datos de cursos
        cur = []
        for inscripcion in inscripciones:
            standard = helper.get_standard(inscripcion)
            if not standard:
                continue

            # Calcular promedios para esta inscripción
            promedios = helper.calcular_promedios_optimizado(inscripcion)

            curso = inscripcion.subject_id.nombre if inscripcion.subject_id else ''
            seccion = standard.code if standard.code else ''

            cur.append({
                'curso': curso,
                'seccion': seccion,
                'nota': promedios.get('promedio_notas', 0.0),
                'status': promedios.get('estado', ''),
            })

        data = {
            'form_data': form_data,
            'est': est,
            'cur': cur,
            'signer': signer.id if signer else False,
        }

        return self.env.ref('report_class.action_report_record_fi') \
            .with_context(active_test=False) \
            .report_action(self, data=data)