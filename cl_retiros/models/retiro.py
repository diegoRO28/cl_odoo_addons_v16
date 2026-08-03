# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StudentInscripcion(models.Model):
    _inherit = 'student.inscripcion'

    state_aux = fields.Selection(
        selection_add=[('flotante', 'Flotante')],
        ondelete={'flotante': 'cascade'},
        store=True,
        default='preinscrito',          # valor válido
    )

    @api.depends('state')
    def _compute_state(self):
        """Sobreescribimos el compute del padre para respetar el estado Flotante."""
        for rec in self:
            flotante_retiro = self.env['student.retiro'].search([
                ('ri_id', '=', rec.id),
                ('state', '=', 'flotante'),
            ], limit=1)

            if flotante_retiro:
                rec.state_aux = 'flotante'
            else:
                rec.state_aux = self.get_estado(rec.state)


class StudentRetiro(models.Model):
    _inherit = 'student.retiro'

    state = fields.Selection(
        selection_add=[
            ('flotante', 'Flotante'),
            ('terminate', 'Retirado'),
            ('cancel', 'Reinscrito'),
        ],
        ondelete={'flotante': 'cascade'}
    )

    is_flotante = fields.Boolean(string='Es Flotante?', default=False, readonly=True)

    def action_set_flotante(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError("Solo se puede poner en estado Flotante un registro de retiro en borrador.")

            rec.state = 'flotante'
            rec.is_flotante = True

            if rec.ri_id:
                rec.ri_id.state = 'done'
                rec.student_id.state = 'done'
                # Forzamos el recálculo del state_aux
                rec.ri_id._compute_state()

                rec.standard_id._compute_total_student()
                self._remove_from_active_asistencias(rec)

    def action_reactivate(self):
        for rec in self:
            if rec.state != 'flotante':
                raise ValidationError("Solo se puede reactivar un registro que esté en estado Flotante.")

            if rec.ri_id:
                rec.ri_id.state = 'done'
                rec.student_id.state = 'done'
                rec.ri_id._compute_state()

            rec.is_flotante = False
            rec.state = 'cancel'          # se muestra como "Reinscrito"

            rec.standard_id._compute_total_student()
            self._add_to_active_asistencias(rec)

    def admission_done(self):
        for rec in self:
            if rec.state == 'flotante':
                super(StudentRetiro, rec).admission_done()
                rec.is_flotante = False
            else:
                super(StudentRetiro, rec).admission_done()

    @api.model
    def create(self, vals):
        if vals.get('state') == 'flotante':
            vals['is_flotante'] = True
        return super(StudentRetiro, self).create(vals)

    def _remove_from_active_asistencias(self, rec):
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


class StandardEvaluacion(models.Model):
    _inherit = 'standard.evaluacion'

    def set_done_corregir(self):
        for rec in self:
            active_students = rec.standard_id.student_ids.filtered(lambda s: s.state == 'done')
            existing_student_ids = rec.evaluacion_ids.mapped('student_id.id')
            missing_students = active_students.filtered(lambda s: s.student_id.id not in existing_student_ids)

            if missing_students:
                evaluacion_obj = self.env['standard.evaluaciones']
                for inscripcion in missing_students:
                    evaluacion_obj.create({
                        'inscripcion_id': inscripcion.id,
                        'evaluacion_id': rec.id,
                        'student_id': inscripcion.student_id.id,
                    })

            super(StandardEvaluacion, rec).set_done_corregir()