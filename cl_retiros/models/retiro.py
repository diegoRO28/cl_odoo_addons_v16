# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError

class StudentRetiro(models.Model):
    _inherit = 'student.retiro'

    # ---------------------------------------------------------------------
    # 1. Extendemos la lista de estados del campo 'state' del RETIRO
    #    (Esto es seguro porque el modelo 'student.retiro' sí acepta nuevos estados).
    # ---------------------------------------------------------------------
    state = fields.Selection(
        selection_add=[('flotante', 'Flotante')],
        ondelete={'flotante': 'cascade'}
    )

    # ---------------------------------------------------------------------
    # 2. Campo booleano de control interno para saber si está en flotante
    # ---------------------------------------------------------------------
    is_flotante = fields.Boolean(string='Es Flotante?', default=False, readonly=True)

    # ==============================================================
    # ACCIÓN 1: PASAR DE INSCRITO A FLOTANTE (Botón "PONER FLOTANTE")
    # ==============================================================
    def action_set_flotante(self):
        for rec in self:
            # Solo se puede poner flotante si el registro de retiro está en borrador
            if rec.state != 'draft':
                raise ValidationError("Solo se puede poner en estado Flotante un registro de retiro en borrador.")

            # 1. Cambiamos el estado de este registro de retiro a 'flotante'
            rec.state = 'flotante'
            rec.is_flotante = True

            # 2. Actualizamos el estado del Registro de Inscripción (RI) original del estudiante
            #    IMPORTANTE: El padre NO acepta 'flotante'. Le ponemos 'retirado' (que sí acepta).
            rec.ri_id.state_aux = 'retirado'
            rec.ri_id.state = 'cancel'

            # 3. Actualizamos el estado del Estudiante Padre
            #    El padre student.student NO acepta 'flotante'. Le ponemos 'terminate'.
            rec.student_id.state = 'terminate'

            # 4. Forzamos el recálculo de los contadores de la sección (el estudiante sale de los cupos activos)
            rec.standard_id._compute_total_student()

    # ==============================================================
    # ACCIÓN 2: VOLVER DE FLOTANTE A INSCRITO (Botón "REACTIVAR INSCRIPCIÓN")
    # ==============================================================
    def action_reactivate(self):
        for rec in self:
            # Solo se puede reactivar si el registro está en flotante
            if rec.state != 'flotante':
                raise ValidationError("Solo se puede reactivar un registro que esté en estado Flotante.")

            # 1. Devolvemos el RI a 'inscrito' (Valor permitido por el padre)
            rec.ri_id.state_aux = 'inscrito'
            rec.ri_id.state = 'done'

            # 2. Devolvemos el estudiante a 'done' (Valor permitido por el padre)
            rec.student_id.state = 'done'

            # 3. Limpiamos el flag de flotante
            rec.is_flotante = False

            # 4. Como ya no está flotante, el registro de retiro ya no es necesario.
            #    Lo marcamos como 'cancel' para que desaparezca de la lista activa de retiros.
            rec.state = 'cancel'

            # 5. Recalculamos la sección (el estudiante vuelve a los cupos)
            rec.standard_id._compute_total_student()

    # ==============================================================
    # ACCIÓN 3: PASAR DE FLOTANTE A RETIRADO DEFINITIVO (Botón "CONFIRMAR RETIRO" del padre)
    # ==============================================================
    def admission_done(self):
        """Sobrescribimos parcialmente el método del padre para manejar el flujo desde Flotante."""
        for rec in self:
            if rec.state == 'flotante':
                # Llamamos al método original del padre para que ejecute el retiro real
                super(StudentRetiro, rec).admission_done()
                
                # Limpiamos el flag de flotante
                rec.is_flotante = False
            else:
                # Si no está en flotante, llamamos al padre directamente (comportamiento original)
                super(StudentRetiro, rec).admission_done()

    # ==============================================================
    # Lógica de Create (Asegurar que los campos locales se llenen al crear el registro)
    # ==============================================================
    @api.model
    def create(self, vals):
        # Si el registro se crea directamente en flotante (por si acaso), aseguramos el flag
        if vals.get('state') == 'flotante':
            vals['is_flotante'] = True
        res = super(StudentRetiro, self).create(vals)
        return res