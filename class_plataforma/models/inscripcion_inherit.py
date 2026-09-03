# See LICENSE file for full copyright and licensing details.

import logging
import time
from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class StudentInscripcionMoodle(models.Model):
    """Integración con Moodle sobre student.inscripcion (Opción B).

    No se toca 'school': todos los campos y la lógica de sincronización
    viven aquí. Al desinstalar este módulo, student.inscripcion vuelve
    a quedar exactamente como en el módulo original.
    """

    _inherit = 'student.inscripcion'

    moodle_enrolled = fields.Boolean(
        string='Inscrito en Moodle', default=False, copy=False,
        help="Indica si el estudiante ya fue sincronizado con Moodle.",
    )
    moodle_course_id = fields.Integer(
        string='ID del curso en Moodle (cache)', copy=False,
        help="ID del curso en Moodle obtenido en la última sincronización "
             "de esta inscripción.",
    )
    moodle_sync_error = fields.Boolean(
        string='Error en sincronización', default=False, copy=False,
    )
    moodle_error_message = fields.Text(
        string='Mensaje de error Moodle', readonly=True, copy=False,
    )

    # ------------------------------------------------------------------
    # Hook: se dispara automáticamente al confirmar la inscripción
    # ------------------------------------------------------------------
    def admission_done(self):
        res = super().admission_done()
        for record in self:
            try:
                record.action_sync_moodle()
            except Exception as e:
                record.moodle_sync_error = True
                record.moodle_error_message = str(e)
                record.message_post(
                    body=_("Error al sincronizar con Moodle: %s") % e
                )
                _logger.exception(
                    "Error al sincronizar inscripción %s con Moodle", record.name
                )
        return res

    # ------------------------------------------------------------------
    # Helpers de datos del estudiante (misma lógica que el original)
    # ------------------------------------------------------------------
    def _get_moodle_student_names(self):
        """Devuelve (student_code, firstname, lastname) para Moodle."""
        self.ensure_one()
        partner = self.student_partner_id
        student_code = self.student_code or "SIN_CODIGO"
        full_name = partner.name or self.student_id.student_name or "Estudiante"
        parts = full_name.strip().split()
        n = len(parts)

        if n <= 1:
            first_name, last_name = full_name, full_name
        elif n == 2:
            first_name, last_name = parts[0], parts[1]
        elif n == 3:
            first_name, last_name = f"{parts[0]} {parts[1]}", parts[2]
        else:  # 4 o más palabras
            first_name, last_name = f"{parts[0]} {parts[1]}", " ".join(parts[2:])

        # Nombre en Moodle: código + nombre, para identificarlo fácil
        firstname = f"{student_code} {first_name}" if first_name else student_code
        lastname = last_name
        return student_code, firstname, lastname

    def _get_moodle_email(self):
        self.ensure_one()
        partner = self.student_partner_id
        email = partner.email
        if not email:
            user_partner = self.student_id.user_id.partner_id
            if user_partner and user_partner.email:
                email = user_partner.email
        if not email:
            student_code = self.student_code or "SIN_CODIGO"
            email = f"{student_code}@cursoscleveland.com"
        return email

    # ------------------------------------------------------------------
    # Orquestación principal (equivalente al action_sync_moodle original,
    # pero delegando el HTTP a moodle.client y la config a moodle.config)
    # ------------------------------------------------------------------
    def action_sync_moodle(self):
        """Crea/actualiza el usuario en Moodle y lo matricula en su curso."""
        client = self.env['moodle.client']
        config = self.env['moodle.config'].get_active_config()

        for record in self:
            partner = record.student_partner_id
            if not partner:
                raise UserError(_(
                    "No se encontró el Partner o usuario asociado al estudiante."
                ))

            student_code, firstname, lastname = record._get_moodle_student_names()
            username = student_code
            email = record._get_moodle_email()

            # ---------- 1. Curso en Moodle ----------
            code_moodle = record.standard_id.subject_id.code_moodle
            if not code_moodle:
                raise UserError(_(
                    "El curso '%s' no tiene asignado un 'Código Moodle'.\n"
                    "Configure el campo 'Código Moodle' en el curso."
                ) % record.standard_id.subject_id.name)

            course = client.search_course_by_shortname(
                code_moodle, config=config, inscripcion=record
            )
            if not course:
                raise UserError(_(
                    "No se encontró un curso en Moodle con el código '%s'."
                ) % code_moodle)

            moodle_course_id = course.get('id')
            record.moodle_course_id = moodle_course_id
            record.standard_id.moodle_course_id = moodle_course_id

            # ---------- 2. Usuario en Moodle (buscar por username o email) ----------
            user = client.get_user_by_field(
                'username', username, config=config, inscripcion=record
            )
            if not user:
                user = client.get_user_by_field(
                    'email', email, config=config, inscripcion=record
                )

            user_vals = {
                'email': email,
                'firstname': firstname,
                'lastname': lastname,
                'password': config.default_password,
                'city': config.default_city,
                'country': config.default_country,
            }

            if user:
                moodle_user_id = user.get('id')
                client.update_user(
                    {**user_vals, 'id': moodle_user_id},
                    config=config, inscripcion=record,
                )
            else:
                user_vals.update({'username': username, 'auth': 'manual'})
                moodle_user_id = client.create_user(
                    user_vals, config=config, inscripcion=record
                )

            if not moodle_user_id:
                raise UserError(_(
                    "No se pudo obtener ni generar el ID del usuario en Moodle."
                ))

            # ---------- 3. Matrícula ----------
            timestart = int(time.mktime(record.inscription_date.timetuple()))
            invoice_due_date = (
                record.move_id.invoice_date_due
                or (fields.Date.today() + timedelta(days=30))
            )
            moodle_expiry_date = invoice_due_date + timedelta(days=1)
            timeend = int(time.mktime(moodle_expiry_date.timetuple()))

            client.enrol_user(
                moodle_user_id, moodle_course_id, timestart, timeend,
                role_id=config.enrol_role_id, config=config, inscripcion=record,
            )

            record.moodle_enrolled = True
            record.moodle_sync_error = False
            record.moodle_error_message = False
            _logger.info(
                "Sincronización Moodle completada para %s (usuario %s)",
                record.name, username,
            )

        return True

    # ------------------------------------------------------------------
    # Reintento manual desde el botón "Inscribir en Moodle" del formulario
    # ------------------------------------------------------------------
    def action_retry_sync_moodle(self):
        """Reintento manual. A diferencia de llamar action_sync_moodle()
        directo desde un botón, este método SIEMPRE atrapa el error: si se
        deja escapar la excepción, Odoo revierte toda la transacción,
        incluyendo los registros de moodle.sync.log recién creados, que es
        justo la evidencia que queremos conservar cuando algo falla.
        """
        self.ensure_one()
        try:
            self.action_sync_moodle()
        except Exception as e:
            self.moodle_sync_error = True
            self.moodle_error_message = str(e)
            self.message_post(
                body=_("Error al sincronizar con Moodle: %s") % e
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error al sincronizar con Moodle'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sincronización exitosa'),
                'message': _('El estudiante quedó matriculado en Moodle.'),
                'type': 'success',
                'sticky': False,
            },
        }
