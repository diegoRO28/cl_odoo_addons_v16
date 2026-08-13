# -*- coding: utf-8 -*-

import logging
from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ReportHelperOptimized(models.AbstractModel):
    _name = "report.helper.optimized"
    _description = "Helper Optimizado para Reportes Académicos"

    # ============================================================
    # MÉTODOS PARA INCLUIR REGISTROS ARCHIVADOS
    # ============================================================

    def get_student(self, student_id):
        """
        Obtiene el estudiante incluyendo registros archivados.
        """
        _logger.info(f"Buscando estudiante con ID: {student_id}")
        student = self.env['student.student']\
            .sudo()\
            .with_context(active_test=False)\
            .browse(student_id)

        if not student.exists():
            _logger.error(f"Estudiante no encontrado con ID: {student_id}")
            raise UserError("No se encontró el estudiante.")

        return student

    def get_inscripcion(self, inscripcion_id):
        """
        Obtiene la inscripción incluyendo registros archivados.
        """
        _logger.info(f"Buscando inscripción con ID: {inscripcion_id}")
        inscripcion = self.env['student.inscripcion']\
            .sudo()\
            .with_context(active_test=False)\
            .browse(inscripcion_id)

        if not inscripcion.exists():
            _logger.error(f"Inscripción no encontrada con ID: {inscripcion_id}")
            raise UserError("No se encontró la inscripción.")

        return inscripcion

    def get_standard(self, inscripcion):
        """
        Obtiene la sección incluyendo registros archivados.
        """
        if not inscripcion.standard_id:
            return False

        return self.env['school.standard']\
            .sudo()\
            .with_context(active_test=False)\
            .browse(inscripcion.standard_id.id)

    def get_evaluaciones(self, standard):
        """
        Obtiene las evaluaciones de la sección incluyendo archivadas.
        """
        return self.env['standard.evaluacion']\
            .sudo()\
            .with_context(active_test=False)\
            .search([
                ('standard_id', '=', standard.id),
                ('state', '=', 'terminate')
            ])

    def get_evaluacion_detalle(self, evaluacion, student):
        """
        Obtiene el detalle de evaluación del estudiante incluyendo archivados.
        """
        return self.env['standard.evaluaciones']\
            .sudo()\
            .with_context(active_test=False)\
            .search([
                ('evaluacion_id', '=', evaluacion.id),
                ('student_id', '=', student.id)
            ])

    def get_actividades(self, evaluacion_detalle):
        """
        Obtiene las actividades de la evaluación incluyendo archivadas.
        """
        return self.env['standard.actividades']\
            .sudo()\
            .with_context(active_test=False)\
            .search([
                ('evaluacion_id', '=', evaluacion_detalle.id)
            ])

    def get_asistencias(self, standard):
        """
        Obtiene las asistencias de la sección incluyendo archivadas.
        """
        return self.env['subject.asistencia']\
            .sudo()\
            .with_context(active_test=False)\
            .search([
                ('standard_id', '=', standard.id),
                ('state', '=', 'terminate')
            ])

    def get_asistencia_detalle(self, asistencia, student):
        """
        Obtiene el detalle de asistencia del estudiante incluyendo archivados.
        """
        return self.env['subject.asistencias']\
            .sudo()\
            .with_context(active_test=False)\
            .search([
                ('asistencia_id', '=', asistencia.id),
                ('student_id', '=', student.id)
            ])

    def get_inscripciones_historicas(self, student):
        """
        Obtiene todas las inscripciones históricas del estudiante
        incluyendo las de secciones archivadas.
        """
        return self.env['student.inscripcion']\
            .sudo()\
            .with_context(active_test=False)\
            .search([
                ('student_id', '=', student.id),
                ('state', 'in', ['done', 'terminate'])
            ])

    def get_escala(self):
        """
        Obtiene la escala de calificación.
        """
        califica_vals = {'minimo': 0, 'maximo': 0, 'aprobado': 0}
        escalaObj = self.env['grade.line'].sudo().with_context(active_test=False).search([('sequence', '=', '1')], limit=1)
        if escalaObj:
            califica_vals = {
                'minimo': escalaObj.from_mark,
                'maximo': escalaObj.to_mark,
                'aprobado': escalaObj.pass_mark
            }
        return califica_vals

    def calcular_promedios_optimizado(self, inscripcion):
        """
        Calcula los promedios del estudiante asegurando que se usen
        los datos de secciones archivadas.
        """
        student = inscripcion.student_id
        standard = self.get_standard(inscripcion)

        if not standard:
            return {
                'promedio_notas': 0.0,
                'promedio_asistencia': 0.0,
                'cantidad_evaluaciones': 0,
                'cantidad_asistencias': 0,
                'estado': 'SIN SECCIÓN',
            }

        # Obtener evaluaciones y asistencias
        evaluaciones = self.get_evaluaciones(standard)
        asistencias = self.get_asistencias(standard)

        total_evaluaciones = len(evaluaciones)
        total_asistencias = len(asistencias)
        total_presentes = 0
        suma_notas = 0.0

        # Calcular evaluaciones
        for evaluacion in evaluaciones:
            detalle = self.get_evaluacion_detalle(evaluacion, student)
            for det in detalle:
                if det.nota:
                    suma_notas += det.nota

        # Calcular asistencias
        for asistencia in asistencias:
            detalle = self.get_asistencia_detalle(asistencia, student)
            for det in detalle:
                if det.is_attended:
                    total_presentes += 1

        # Calcular promedios
        promedio_notas = inscripcion.nota or 0.0

        if not promedio_notas and total_evaluaciones > 0:
            promedio_notas = suma_notas / total_evaluaciones

        promedio_asistencia = 0.0
        if total_asistencias > 0:
            promedio_asistencia = (total_presentes / total_asistencias) * 100

        # Determinar estado
        escala = self.get_escala()
        estado = "APLAZADO"
        if promedio_notas >= escala.get('aprobado', 10):
            estado = "APROBADO"

        return {
            'promedio_notas': promedio_notas,
            'promedio_asistencia': promedio_asistencia,
            'cantidad_evaluaciones': total_evaluaciones,
            'cantidad_asistencias': total_asistencias,
            'estado': estado,
        }