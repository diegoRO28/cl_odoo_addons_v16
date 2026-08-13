# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.exceptions import UserError


class ReportHelperOptimized(models.AbstractModel):
    _name = "report.helper.optimized"
    _description = "Helper Optimizado para Reportes Académicos"
    # NO hereda de report.helper porque no existe en report_class

    # ============================================================
    # MÉTODOS PARA INCLUIR REGISTROS ARCHIVADOS
    # ============================================================

    def get_student(self, student_id):
        """
        Obtiene el estudiante incluyendo registros archivados.
        """
        student = self.env['student.student']\
            .sudo()\
            .with_context(active_test=False)\
            .browse(student_id)

        if not student.exists():
            raise UserError("No se encontró el estudiante.")

        return student

    def get_inscripcion(self, inscripcion_id):
        """
        Obtiene la inscripción incluyendo registros archivados.
        """
        inscripcion = self.env['student.inscripcion']\
            .sudo()\
            .with_context(active_test=False)\
            .browse(inscripcion_id)

        if not inscripcion.exists():
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

    def get_report_data_optimized(self, student_id, inscripcion_id=None):
        """
        Obtiene todos los datos del reporte incluyendo secciones archivadas.
        """
        student = self.get_student(student_id)
        
        data = {
            'student': student,
            'inscripcion': None,
            'standard': None,
            'evaluaciones': [],
            'asistencias': [],
            'inscripciones_historicas': [],
            'promedios': {},
        }

        # Si se especifica una inscripción, obtener sus datos
        if inscripcion_id:
            inscripcion = self.get_inscripcion(inscripcion_id)
            data['inscripcion'] = inscripcion
            standard = self.get_standard(inscripcion)
            data['standard'] = standard

            if standard:
                data['evaluaciones'] = self.get_evaluaciones(standard)
                data['asistencias'] = self.get_asistencias(standard)
                data['promedios'] = self.calcular_promedios_optimizado(inscripcion)

        # Siempre obtener las inscripciones históricas
        data['inscripciones_historicas'] = self.get_inscripciones_historicas(student)

        return data