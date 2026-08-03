# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StudentInscripcion(models.Model):
    _inherit = 'student.inscripcion'

    state_aux = fields.Selection(
        selection_add=[('flotante', 'Flotante')],
        ondelete={'flotante': 'cascade'}
    )


class StudentRetiro(models.Model):
    _inherit = 'student.retiro'

    # Extendemos el estado y cambiamos las etiquetas
    state = fields.Selection(
        selection_add=[
            ('flotante', 'Flotante'),
            ('terminate', 'Retirado'),
            ('cancel', 'Reinscrito'),      # ← nueva etiqueta
        ],
        ondelete={'flotante': 'cascade'}
    )

    is_flotante = fields.Boolean(string='Es Flotante?', default=False, readonly=True)

    # ==============================================================
    # ACCIÓN 1: PASAR DE INSCRITO A FLOTANTE
    # ==============================================================
    def action_set_flotante(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError("Solo se puede poner en estado Flotante un registro de retiro en borrador.")

            rec.state = 'flotante'
            rec.is_flotante = True

            # Cambiamos state_aux del RI a 'flotante'
            if rec.ri_id:
                rec.ri_id.state_aux = 'flotante'
                rec.ri_id.state = 'done'
                rec.student_id.state = 'done'

                # Recalcular cupos (libera el cupo)
                rec.standard_id._compute_total_student()

                # Eliminar al estudiante de asistencias activas
                self._remove_from_active_asistencias(rec)

    # ==============================================================
    # ACCIÓN 2: VOLVER DE FLOTANTE A INSCRITO
    # ==============================================================
    def action_reactivate(self):
        for rec in self:
            if rec.state != 'flotante':
                raise ValidationError("Solo se puede reactivar un registro que esté en estado Flotante.")

            # Volver a 'inscrito'
            if rec.ri_id:
                rec.ri_id.state_aux = 'inscrito'
                rec.ri_id.state = 'done'
                rec.student_id.state = 'done'

            rec.is_flotante = False
            rec.state = 'cancel'  # El retiro se cancela

            # Recalcular cupos (ocupa el cupo nuevamente)
            rec.standard_id._compute_total_student()

            # Volver a agregar al estudiante a asistencias activas
            self._add_to_active_asistencias(rec)

    # ==============================================================
    # ACCIÓN 3: PASAR DE FLOTANTE A RETIRADO DEFINITIVO
    # ==============================================================
    def admission_done(self):
        for rec in self:
            if rec.state == 'flotante':
                # Llamamos al padre para que haga el retiro definitivo
                super(StudentRetiro, rec).admission_done()
                rec.is_flotante = False
            else:
                super(StudentRetiro, rec).admission_done()

    # ==============================================================
    # Lógica de Create
    # ==============================================================
    @api.model
    def create(self, vals):
        if vals.get('state') == 'flotante':
            vals['is_flotante'] = True
        return super(StudentRetiro, self).create(vals)

    # =========================================================================
    # MÉTODOS AUXILIARES PARA MANEJAR LAS ASISTENCIAS
    # =========================================================================

    def _remove_from_active_asistencias(self, rec):
        """Elimina al estudiante de todas las asistencias activas de la sección."""
        if not rec.ri_id or not rec.standard_id:
            return

        active_asistencias = rec.standard_id.asistencia_ids.filtered(
            lambda a: a.state in ['draft', 'done']
        )
        if active_asistencias:
            asistencias_estudiante = self.env['subject.asistencias'].search([
                ('inscripcion_id', '=', rec.ri_id.id),
                ('asistencia_id', 'in', active_asistencias.ids)
            ])
            if asistencias_estudiante:
                asistencias_estudiante.unlink()

    def _add_to_active_asistencias(self, rec):
        """Re-agrega al estudiante a las asistencias activas de la sección."""
        if not rec.ri_id or not rec.standard_id:
            return

        active_asistencias = rec.standard_id.asistencia_ids.filtered(
            lambda a: a.state in ['draft', 'done']
        )
        if active_asistencias:
            existing_asistencias = self.env['subject.asistencias'].search([
                ('inscripcion_id', '=', rec.ri_id.id),
                ('asistencia_id', 'in', active_asistencias.ids)
            ])
            existing_asistencia_ids = existing_asistencias.mapped('asistencia_id.id')
            missing_asistencias = active_asistencias.filtered(
                lambda a: a.id not in existing_asistencia_ids
            )
            if missing_asistencias:
                asistencias_obj = self.env['subject.asistencias']
                for asistencia in missing_asistencias:
                    asistencias_obj.create({
                        'inscripcion_id': rec.ri_id.id,
                        'asistencia_id': asistencia.id,
                        'student_id': rec.student_id.id,
                        'is_attended': True,
                        'note': "Reactivado desde Flotante",
                    })


# =============================================================================
# CLASE PARA MANEJAR EL ERROR DE EVALUACIONES
# =============================================================================

class StandardEvaluacion(models.Model):
    _inherit = 'standard.evaluacion'

    def set_done_corregir(self):
        """
        Sobrescribimos parcialmente este método del padre.
        Antes de poner la evaluación en 'draft', nos aseguramos de que
        TODOS los estudiantes activos (state='done') tengan su registro
        en evaluacion_ids.
        """
        for rec in self:
            # 1. Obtener todos los estudiantes activos de la sección
            active_students = rec.standard_id.student_ids.filtered(lambda s: s.state == 'done')

            # 2. Obtener los IDs de los estudiantes que YA tienen registro en esta evaluación
            existing_student_ids = rec.evaluacion_ids.mapped('student_id.id')

            # 3. Identificar a los estudiantes FALTANTES
            missing_students = active_students.filtered(lambda s: s.student_id.id not in existing_student_ids)

            # 4. Si hay faltantes, los CREAMOS antes de continuar
            if missing_students:
                evaluacion_obj = self.env['standard.evaluaciones']
                for inscripcion in missing_students:
                    evaluacion_obj.create({
                        'inscripcion_id': inscripcion.id,
                        'evaluacion_id': rec.id,
                        'student_id': inscripcion.student_id.id,
                    })

            # 5. Ahora que la lista está completa, llamamos al método original del padre
            super(StandardEvaluacion, rec).set_done_corregir()