# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StudentInscripcion(models.Model):
    _inherit = 'student.inscripcion'

    is_flotante = fields.Boolean(
        string='Es Flotante?',
        default=False,
        readonly=True,
        copy=False,
    )


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
                raise ValidationError(
                    "Solo se puede poner en estado Flotante un registro de retiro en borrador."
                )

            rec.state = 'flotante'
            rec.is_flotante = True

            if rec.ri_id:
                rec.ri_id.write({
                    'state': 'done',
                    'is_flotante': True,
                })
                rec.student_id.state = 'done'

                if hasattr(rec.ri_id, '_compute_state'):
                    rec.ri_id._compute_state()

                rec.standard_id._compute_total_student()
                self._remove_from_active_asistencias(rec)
                self._ensure_in_evaluaciones(rec)

    def action_reactivate(self):
        for rec in self:
            if rec.state != 'flotante':
                raise ValidationError(
                    "Solo se puede reactivar un registro que esté en estado Flotante."
                )

            if rec.ri_id:
                rec.ri_id.write({
                    'state': 'done',
                    'is_flotante': False,
                })
                rec.student_id.state = 'done'
                if hasattr(rec.ri_id, '_compute_state'):
                    rec.ri_id._compute_state()

            rec.is_flotante = False
            rec.state = 'cancel'  # se muestra como "Reinscrito"

            rec.standard_id._compute_total_student()
            self._add_to_active_asistencias(rec)

    def admission_done(self):
        for rec in self:
            if rec.state == 'flotante':
                super(StudentRetiro, rec).admission_done()
                rec.is_flotante = False
                if rec.ri_id:
                    rec.ri_id.is_flotante = False
            else:
                super(StudentRetiro, rec).admission_done()

    @api.model
    def create(self, vals):
        if vals.get('state') == 'flotante':
            vals['is_flotante'] = True
        return super(StudentRetiro, self).create(vals)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _remove_from_active_asistencias(self, rec):
        if not rec.ri_id or not rec.standard_id:
            return
        active_asistencias = rec.standard_id.asistencia_ids.filtered(
            lambda a: a.state in ['draft', 'done']
        )
        if active_asistencias:
            asistencias_estudiante = self.env['subject.asistencias'].search([
                ('inscripcion_id', '=', rec.ri_id.id),
                ('asistencia_id', 'in', active_asistencias.ids),
            ])
            if asistencias_estudiante:
                asistencias_estudiante.unlink()

    def _add_to_active_asistencias(self, rec):
        """
        Al reactivar: agrega al estudiante en asistencias activas
        SIN nota especial y SIN duplicar.
        """
        if not rec.ri_id or not rec.standard_id:
            return

        active_asistencias = rec.standard_id.asistencia_ids.filtered(
            lambda a: a.state in ['draft', 'done']
        )
        if not active_asistencias:
            return

        existing = self.env['subject.asistencias'].search([
            ('inscripcion_id', '=', rec.ri_id.id),
            ('asistencia_id', 'in', active_asistencias.ids),
        ])
        existing_asistencia_ids = existing.mapped('asistencia_id.id')

        missing = active_asistencias.filtered(
            lambda a: a.id not in existing_asistencia_ids
        )

        for asistencia in missing:
            self.env['subject.asistencias'].create({
                'inscripcion_id': rec.ri_id.id,
                'asistencia_id': asistencia.id,
                'student_id': rec.student_id.id,
                'is_attended': True,
                'note': ' ',  # sin "Reactivado desde Flotante"
            })

    def _ensure_in_evaluaciones(self, rec):
        """
        Garantiza que el estudiante flotante tenga registro en las evaluaciones
        que YA están iniciadas (igual que un alumno normal).
        NO crea líneas cuando la evaluación está en draft (POR INICIAR);
        eso lo hace el generate_record_evaluacion del módulo padre al iniciar.
        """
        if not rec.ri_id or not rec.standard_id:
            return
    
        # Solo evaluaciones ya iniciadas / culminadas / recuperación
        # (igual que el padre: las de draft se generan al hacer set_done)
        evaluaciones = rec.standard_id.registroeva_ids.filtered(
            lambda e: e.state in ('done', 'terminate', 'recovery')
        )
        if not evaluaciones:
            return
    
        evaluacion_obj = self.env['standard.evaluaciones']
        for eva in evaluaciones:
            existe = eva.evaluacion_ids.filtered(
                lambda l: l.inscripcion_id.id == rec.ri_id.id
            )
            if existe:
                continue
    
            # Crear exactamente igual que un alumno normal
            evalua_id = evaluacion_obj.create({
                'inscripcion_id': rec.ri_id.id,
                'evaluacion_id': eva.id,
                'student_id': rec.student_id.id,
            })
    
            if eva.libroevas_id and eva.libroevas_id.actividad_ids:
                no_act = len(eva.libroevas_id.actividad_ids)
                for r in range(1, no_act + 1):
                    act = eva.libroevas_id.actividad_ids[r - 1]
                    if r == 1:
                        evalua_id.is_act1 = True
                        evalua_id.actividad1_id = act.id
                    elif r == 2:
                        evalua_id.is_act2 = True
                        evalua_id.actividad2_id = act.id
                    elif r == 3:
                        evalua_id.is_act3 = True
                        evalua_id.actividad3_id = act.id
                    elif r == 4:
                        evalua_id.is_act4 = True
                        evalua_id.actividad4_id = act.id
                    elif r == 5:
                        evalua_id.is_act5 = True
                        evalua_id.actividad5_id = act.id
                    elif r == 6:
                        evalua_id.is_act6 = True
                        evalua_id.actividad6_id = act.id


class SchoolStandard(models.Model):
    _inherit = 'school.standard'

    @api.depends('student_ids', 'student_ids.state', 'student_ids.is_flotante')
    def _compute_total_student(self):
        """Los estudiantes flotantes NO ocupan cupo."""
        for record in self:
            line_obj = record.student_ids
            line_cancel = line_obj.filtered(lambda x: x.state in ['cancel'])
            line_done = line_obj.filtered(
                lambda x: x.state in ['done'] and not x.is_flotante
            )

            record.total_students = len(line_done)
            record.total_students_cancel = len(line_cancel)
            record.remaining_seats = record.capacity - len(line_done)


class StandardEvaluacion(models.Model):
    _inherit = 'standard.evaluacion'

    def get_no_students(self):
        contador = 0
        for rec in self:
            line_obj = rec.standard_id.student_ids
            # Incluye flotantes (state=done) porque deben aparecer en evaluaciones
            line_inscritos = line_obj.filtered(lambda x: x.state == 'done')
            contador = len(line_inscritos)
        return contador

    def generate_record_evaluacion(self, no_students):
        """
        Genera registros de evaluación.
        - Incluye estudiantes con state='done' (normales + flotantes).
        - NO crea duplicados si la línea ya existe.
        """
        evaluacion_obj = self.env['standard.evaluaciones']

        for rec in self:
            active_students = rec.standard_id.student_ids.filtered(
                lambda s: s.state == 'done'
            )
            # IDs de inscripciones que YA tienen línea en esta evaluación
            existing_ri_ids = rec.evaluacion_ids.mapped('inscripcion_id.id')

            for inscripcion in active_students:
                # Evitar duplicados
                if inscripcion.id in existing_ri_ids:
                    continue

                evalua_id = evaluacion_obj.create({
                    'inscripcion_id': inscripcion.id,
                    'evaluacion_id': rec.id,
                    'student_id': inscripcion.student_id.id,
                })

                # Actividades del libro
                if rec.libroevas_id and rec.libroevas_id.actividad_ids:
                    no_act = len(rec.libroevas_id.actividad_ids)
                    for r in range(1, no_act + 1):
                        act = rec.libroevas_id.actividad_ids[r - 1]
                        if r == 1:
                            evalua_id.is_act1 = True
                            evalua_id.actividad1_id = act.id
                            rec.note_act = "A1: " + (act.tipo_id.name or '') + " , "
                        elif r == 2:
                            evalua_id.is_act2 = True
                            evalua_id.actividad2_id = act.id
                            rec.note_act = (rec.note_act or '') + " A2: " + (act.tipo_id.name or '') + " , "
                        elif r == 3:
                            evalua_id.is_act3 = True
                            evalua_id.actividad3_id = act.id
                            rec.note_act = (rec.note_act or '') + " A3: " + (act.tipo_id.name or '') + " , "
                        elif r == 4:
                            evalua_id.is_act4 = True
                            evalua_id.actividad4_id = act.id
                            rec.note_act = (rec.note_act or '') + " A4: " + (act.tipo_id.name or '') + " , "
                        elif r == 5:
                            evalua_id.is_act5 = True
                            evalua_id.actividad5_id = act.id
                            rec.note_act = (rec.note_act or '') + " A5: " + (act.tipo_id.name or '') + " , "
                        elif r == 6:
                            evalua_id.is_act6 = True
                            evalua_id.actividad6_id = act.id

    def _dedup_evaluacion_lines(self, rec):
        """
        Elimina líneas duplicadas en standard.evaluaciones para una misma
        combinación (inscripcion_id, evaluacion). Deja solo la más antigua
        (menor id) y borra el resto.

        Esto es una red de seguridad: sin importar si el módulo padre
        crea líneas por su cuenta o si esta clase también lo hace,
        al final de set_done()/set_terminate() nunca deben quedar
        estudiantes repetidos.
        """
        seen = {}
        to_unlink = self.env['standard.evaluaciones']
        for line in rec.evaluacion_ids.sorted('id'):
            key = line.inscripcion_id.id
            if key in seen:
                to_unlink |= line
            else:
                seen[key] = line
        if to_unlink:
            to_unlink.unlink()

    def set_done_corregir(self):
        """
        CORREGIDO: Al volver a iniciado, resetea TODOS los registros a 'borrador'
        y sincroniza TODOS los estudiantes activos (incluyendo flotantes)
        """
        for rec in self:
            # 1. VERIFICAR que la sección no esté culminada
            if rec.state_sta == 'terminate':
                raise ValidationError(_(
                    "Error: No se puede volver a iniciado porque la sección está culminada"
                ))

            # 2. OBTENER todos los estudiantes activos (incluyendo flotantes)
            active_students = rec.standard_id.student_ids.filtered(
                lambda s: s.state == 'done'
            )
            
            # 3. OBTENER IDs de estudiantes que YA tienen registro en esta evaluación
            existing_ri_ids = rec.evaluacion_ids.mapped('inscripcion_id.id')
            
            # 4. AGREGAR estudiantes faltantes (los que no tienen registro)
            missing_students = active_students.filtered(
                lambda s: s.id not in existing_ri_ids
            )

            if missing_students:
                evaluacion_obj = self.env['standard.evaluaciones']
                for inscripcion in missing_students:
                    evalua_id = evaluacion_obj.create({
                        'inscripcion_id': inscripcion.id,
                        'evaluacion_id': rec.id,
                        'student_id': inscripcion.student_id.id,
                    })

                    if rec.libroevas_id and rec.libroevas_id.actividad_ids:
                        no_act = len(rec.libroevas_id.actividad_ids)
                        for r in range(1, no_act + 1):
                            act = rec.libroevas_id.actividad_ids[r - 1]
                            if r == 1:
                                evalua_id.is_act1 = True
                                evalua_id.actividad1_id = act.id
                            elif r == 2:
                                evalua_id.is_act2 = True
                                evalua_id.actividad2_id = act.id
                            elif r == 3:
                                evalua_id.is_act3 = True
                                evalua_id.actividad3_id = act.id
                            elif r == 4:
                                evalua_id.is_act4 = True
                                evalua_id.actividad4_id = act.id
                            elif r == 5:
                                evalua_id.is_act5 = True
                                evalua_id.actividad5_id = act.id
                            elif r == 6:
                                evalua_id.is_act6 = True
                                evalua_id.actividad6_id = act.id

            # 5. Red de seguridad: elimina cualquier duplicado por estudiante
            self._dedup_evaluacion_lines(rec)

            # 6. RESETEAR TODOS los registros a 'borrador' (esto es clave)
            #    Esto incluye a los estudiantes normales Y a los flotantes
            for eval_record in rec.evaluacion_ids:
                eval_record.state = 'borrador'
            
            # 7. Resetear el promedio de la evaluación
            rec.average = 0

            # 8. CAMBIAR el estado de la evaluación a 'done'
            rec.state = 'done'

    def asignar_state_draft(self):
        """
        CORREGIDO: Resetea TODOS los registros de evaluación a 'borrador'
        incluyendo los de estudiantes flotantes.
        """
        for rec in self:
            # Resetear todos los registros existentes
            for eval_record in rec.evaluacion_ids:
                eval_record.state = 'borrador'
            
            rec.average = 0

    def set_terminate(self):
        """
        CORREGIDO: Al cerrar la evaluación, asegura que TODOS los estudiantes
        activos (incluyendo flotantes) tengan su registro.

        IMPORTANTE: la sincronización se hace DESPUÉS de llamar a super(),
        no antes. Crear las líneas manualmente antes de invocar la lógica
        original del padre fue lo que causaba estudiantes duplicados:
        el padre generaba sus propias líneas sin saber que esta clase
        ya las había creado. Además, al final se ejecuta un dedup
        defensivo para garantizar que nunca queden líneas repetidas.
        """
        # 1. Llamar primero al método del padre para que ejecute su lógica de cierre
        result = super(StandardEvaluacion, self).set_terminate()

        # 2. Sincronizar estudiantes activos (incluyendo flotantes) que
        #    el padre no haya contemplado
        for rec in self:
            active_students = rec.standard_id.student_ids.filtered(
                lambda s: s.state == 'done'
            )
            existing_ri_ids = rec.evaluacion_ids.mapped('inscripcion_id.id')
            missing_students = active_students.filtered(
                lambda s: s.id not in existing_ri_ids
            )

            if missing_students:
                evaluacion_obj = self.env['standard.evaluaciones']
                for inscripcion in missing_students:
                    evalua_id = evaluacion_obj.create({
                        'inscripcion_id': inscripcion.id,
                        'evaluacion_id': rec.id,
                        'student_id': inscripcion.student_id.id,
                    })

                    if rec.libroevas_id and rec.libroevas_id.actividad_ids:
                        no_act = len(rec.libroevas_id.actividad_ids)
                        for r in range(1, no_act + 1):
                            act = rec.libroevas_id.actividad_ids[r - 1]
                            if r == 1:
                                evalua_id.is_act1 = True
                                evalua_id.actividad1_id = act.id
                            elif r == 2:
                                evalua_id.is_act2 = True
                                evalua_id.actividad2_id = act.id
                            elif r == 3:
                                evalua_id.is_act3 = True
                                evalua_id.actividad3_id = act.id
                            elif r == 4:
                                evalua_id.is_act4 = True
                                evalua_id.actividad4_id = act.id
                            elif r == 5:
                                evalua_id.is_act5 = True
                                evalua_id.actividad5_id = act.id
                            elif r == 6:
                                evalua_id.is_act6 = True
                                evalua_id.actividad6_id = act.id

            # 3. Red de seguridad: elimina cualquier duplicado por estudiante
            self._dedup_evaluacion_lines(rec)

        return result

    def set_done(self):
        """
        CORREGIDO: Al iniciar la evaluación, asegura que TODOS los estudiantes
        activos (incluyendo flotantes) tengan su registro.

        IMPORTANTE: igual que en set_terminate(), la sincronización ocurre
        DESPUÉS de super() y se aplica un dedup defensivo al final, para
        evitar estudiantes duplicados.
        """
        # 1. Validación previa (esto sí debe ir antes de super())
        for rec in self:
            active_students = rec.standard_id.student_ids.filtered(
                lambda s: s.state == 'done'
            )
            if not active_students:
                raise ValidationError(_("Error: No hay estudiantes activos en el curso"))

        # 2. Llamar al método del padre
        result = super(StandardEvaluacion, self).set_done()

        # 3. Sincronizar estudiantes activos (incluyendo flotantes) que
        #    el padre no haya contemplado
        for rec in self:
            active_students = rec.standard_id.student_ids.filtered(
                lambda s: s.state == 'done'
            )
            existing_ri_ids = rec.evaluacion_ids.mapped('inscripcion_id.id')
            missing_students = active_students.filtered(
                lambda s: s.id not in existing_ri_ids
            )

            if missing_students:
                evaluacion_obj = self.env['standard.evaluaciones']
                for inscripcion in missing_students:
                    evalua_id = evaluacion_obj.create({
                        'inscripcion_id': inscripcion.id,
                        'evaluacion_id': rec.id,
                        'student_id': inscripcion.student_id.id,
                    })

                    if rec.libroevas_id and rec.libroevas_id.actividad_ids:
                        no_act = len(rec.libroevas_id.actividad_ids)
                        for r in range(1, no_act + 1):
                            act = rec.libroevas_id.actividad_ids[r - 1]
                            if r == 1:
                                evalua_id.is_act1 = True
                                evalua_id.actividad1_id = act.id
                            elif r == 2:
                                evalua_id.is_act2 = True
                                evalua_id.actividad2_id = act.id
                            elif r == 3:
                                evalua_id.is_act3 = True
                                evalua_id.actividad3_id = act.id
                            elif r == 4:
                                evalua_id.is_act4 = True
                                evalua_id.actividad4_id = act.id
                            elif r == 5:
                                evalua_id.is_act5 = True
                                evalua_id.actividad5_id = act.id
                            elif r == 6:
                                evalua_id.is_act6 = True
                                evalua_id.actividad6_id = act.id

            # 4. Red de seguridad: elimina cualquier duplicado por estudiante
            self._dedup_evaluacion_lines(rec)

        return result


class SubjectAsistencia(models.Model):
    _inherit = 'subject.asistencia'

    def get_no_students(self):
        """Cuenta solo inscritos activos (no cancelados y no flotantes)."""
        contador = 0
        for rec in self:
            line_obj = rec.standard_id.student_ids
            line_inscritos = line_obj.filtered(
                lambda x: x.state == 'done' and not x.is_flotante
            )
            contador = len(line_inscritos)
        return contador

    def generate_record_attendance(self, no_students):
        """
        Genera registros de asistencia.
        - NO incluye estudiantes flotantes.
        - NO crea duplicados si la línea ya existe.
        """
        asistencia_obj = self.env['subject.asistencias']

        for rec in self:
            active_students = rec.standard_id.student_ids.filtered(
                lambda s: s.state == 'done' and not s.is_flotante
            )
            existing_ri_ids = rec.asistencia_ids.mapped('inscripcion_id.id')

            for inscripcion in active_students:
                if inscripcion.id in existing_ri_ids:
                    continue

                asistencia_obj.create({
                    'inscripcion_id': inscripcion.id,
                    'asistencia_id': rec.id,
                    'student_id': inscripcion.student_id.id,
                    'is_attended': True,
                    'note': ' ',
                })