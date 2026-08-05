# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.exceptions import UserError


class ReportHelper(models.AbstractModel):
    _name = "report.helper"
    _description = "Helper para Reportes Académicos"


    # ============================================================
    # ESTUDIANTE
    # ============================================================
    def get_student(self, student_id):

        student = self.env['student.student']\
            .sudo()\
            .with_context(active_test=False)\
            .browse(student_id)

        if not student.exists():
            raise UserError("No se encontró el estudiante.")

        return student


    # ============================================================
    # INSCRIPCIÓN
    # ============================================================
    def get_inscripcion(self, inscripcion_id):

        inscripcion = self.env['student.inscripcion']\
            .sudo()\
            .with_context(active_test=False)\
            .browse(inscripcion_id)

        if not inscripcion.exists():
            raise UserError("No se encontró la inscripción.")

        return inscripcion


    # ============================================================
    # SECCIÓN
    # ============================================================
    def get_standard(self, inscripcion):

        if not inscripcion.standard_id:
            return False

        return self.env['school.standard']\
            .sudo()\
            .with_context(active_test=False)\
            .browse(inscripcion.standard_id.id)


    # ============================================================
    # EVALUACIONES MAESTRO
    # ============================================================
    def get_evaluaciones(self, standard):

        return self.env['standard.evaluacion']\
            .sudo()\
            .with_context(active_test=False)\
            .search([
                ('standard_id', '=', standard.id),
                ('state', '=', 'terminate')
            ])


    # ============================================================
    # DETALLE DE EVALUACIONES
    # ============================================================
    def get_evaluacion_detalle(self, evaluacion, student):

        return self.env['standard.evaluaciones']\
            .sudo()\
            .with_context(active_test=False)\
            .search([
                ('evaluacion_id', '=', evaluacion.id),
                ('student_id', '=', student.id)
            ])


    # ============================================================
    # ACTIVIDADES
    # ============================================================
    def get_actividades(self, evaluacion_detalle):

        return self.env['standard.actividades']\
            .sudo()\
            .with_context(active_test=False)\
            .search([
                ('evaluacion_id', '=', evaluacion_detalle.id)
            ])


    # ============================================================
    # ASISTENCIAS MAESTRO
    # ============================================================
    def get_asistencias(self, standard):

        return self.env['subject.asistencia']\
            .sudo()\
            .with_context(active_test=False)\
            .search([
                ('standard_id', '=', standard.id),
                ('state', '=', 'terminate')
            ])


    # ============================================================
    # DETALLE ASISTENCIAS
    # ============================================================
    def get_asistencia_detalle(self, asistencia, student):

        return self.env['subject.asistencias']\
            .sudo()\
            .with_context(active_test=False)\
            .search([
                ('asistencia_id', '=', asistencia.id),
                ('student_id', '=', student.id)
            ])


    # ============================================================
    # PROMEDIOS
    # ============================================================
    def calcular_promedios(self, inscripcion,
                           total_evaluaciones,
                           suma_notas,
                           total_asistencias,
                           total_presentes):

        promedio_notas = inscripcion.nota or 0.0

        promedio_asistencia = 0.0

        if total_asistencias:

            promedio_asistencia = (
                total_presentes / total_asistencias
            ) * 100

        return {
            'promedio_notas': promedio_notas,
            'promedio_asistencia': promedio_asistencia,
            'cantidad_evaluaciones': total_evaluaciones,
            'cantidad_asistencias': total_asistencias,
        }


    # ============================================================
    # INFORMACIÓN COMPLETA DEL ESTUDIANTE
    # ============================================================
    def get_report_data(self, student_id, inscripcion_id):

        student = self.get_student(student_id)

        inscripcion = self.get_inscripcion(inscripcion_id)

        standard = self.get_standard(inscripcion)

        if not standard:
            raise UserError("La inscripción no posee sección.")

        evaluaciones = self.get_evaluaciones(standard)

        asistencias = self.get_asistencias(standard)

        return {
            'student': student,
            'inscripcion': inscripcion,
            'standard': standard,
            'evaluaciones': evaluaciones,
            'asistencias': asistencias,
        }