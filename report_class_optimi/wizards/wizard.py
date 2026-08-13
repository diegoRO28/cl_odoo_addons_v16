# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
import calendar
import datetime


class WizardOptimized(models.TransientModel):
    _name = 'report.wizard.optimized'
    _description = 'Report Wizard Optimizado - Record Académico'
    _inherit = 'report.wizard'  # Hereda del wizard original

    def action_search_salida(self):
        """
        Método optimizado para generar el record académico
        incluyendo secciones archivadas.
        """
        form_data = self.read()[0]

        # Usar el helper optimizado
        helper = self.env['report.helper.optimized']

        # Obtener datos del estudiante e inscripción
        student = helper.get_student(self.student_id.id)
        inscripcion = helper.get_inscripcion(self.inscripcion_id.id)
        standard = helper.get_standard(inscripcion)

        # Preparar datos del estudiante
        est = [{
            'cedula': student.student_ci or '',
            'codigo': student.student_code or '',
            'nombre': student.name or '',
            'seccion': standard.code if standard else '',
            'curso': standard.subject_id.nombre if standard and standard.subject_id else '',
            'estado': self.get_estado_estudiante(inscripcion.state),
        }]

        # Preparar datos de evaluaciones
        eva = []
        if standard:
            evaluaciones = helper.get_evaluaciones(standard)
            for evaluacion in evaluaciones:
                detalles = helper.get_evaluacion_detalle(evaluacion, student)
                for detalle in detalles:
                    actividades = helper.get_actividades(detalle)
                    act_list = []
                    for actividad in actividades:
                        act_list.append({
                            'nombreAct': (actividad.nombre or '').upper(),
                            'nota': actividad.nota or 0.0,
                            'nota_r': actividad.nota_r or 0.0,
                        })

                    eva.append({
                        'nombreEva': (evaluacion.nombre or '').upper(),
                        'nota': detalle.nota or 0.0,
                        'nombreSta': detalle.state or '',
                        'noAct': len(act_list),
                        'listAct': act_list,
                    })

        # Preparar datos de asistencias
        asi = []
        if standard:
            asistencias = helper.get_asistencias(standard)
            for asistencia in asistencias:
                detalles = helper.get_asistencia_detalle(asistencia, student)
                for detalle in detalles:
                    nombre_encuentro = ''
                    if asistencia.encuentro_id:
                        nombre_encuentro = asistencia.encuentro_id.name or ''

                    asi.append({
                        'nombreAsi': asistencia.name or '',
                        'encuentro_nombre': nombre_encuentro,
                        'descripcion': asistencia.note or '',
                        'nombreSta': self.get_estado(asistencia.state),
                        'is_asistio': 'ASISTENTE' if detalle.is_attended else 'INASISTENTE',
                    })

        # Calcular promedios
        pro = []
        promedios = helper.calcular_promedios_optimizado(inscripcion)
        pro.append({
            'promeT': promedios.get('promedio_notas', 0.0),
            'promeA': promedios.get('promedio_asistencia', 0.0),
            'nombreSta': promedios.get('estado', ''),
        })

        data = {
            'form_data': form_data,
            'est': est,
            'eva': eva,
            'act': [],
            'asi': asi,
            'pro': pro,
        }

        # Usar el reporte original pero con contexto optimizado
        return self.env.ref('report_class.action_report_record') \
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

    def get_estado_estudiante(self, sta):
        """Mapeo de estados del estudiante."""
        estados = {
            'draft': 'POR INICIAR',
            'done': 'INSCRITO',
            'terminate': 'CULMINADO',
            'cancel': 'RETIRADO',
        }
        return estados.get(sta, sta or '')