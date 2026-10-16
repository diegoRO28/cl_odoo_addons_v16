# See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class StudentRetiroMoodle(models.Model):
    """Integración con Moodle sobre student.retiro.

    Alcance (según lo pedido): el retiro NO saca al estudiante del curso
    en Moodle, solo SUSPENDE su cuenta (bloquea el login). La matrícula
    queda intacta por si se reactiva más adelante.
    """

    _inherit = 'student.retiro'

    moodle_suspended = fields.Boolean(
        string='Suspendido en Moodle', default=False, copy=False,
        help="Indica si la matrícula del estudiante en el curso fue "
             "suspendida en Moodle como parte de este retiro (la cuenta "
             "y el acceso a otros cursos no se ven afectados).",
    )
    moodle_sync_error = fields.Boolean(
        string='Error en sincronización', default=False, copy=False,
    )
    moodle_error_message = fields.Text(
        string='Mensaje de error Moodle', readonly=True, copy=False,
    )

    # ------------------------------------------------------------------
    # Hook: se dispara automáticamente al confirmar el retiro
    # ------------------------------------------------------------------
    def admission_done(self):
        res = super().admission_done()
        for record in self:
            try:
                record.action_sync_moodle_retiro()
            except Exception as e:
                record.moodle_sync_error = True
                record.moodle_error_message = str(e)
                record.message_post(
                    body=_("Error al sincronizar con Moodle: %s") % e
                )
                _logger.exception(
                    "Error al sincronizar retiro %s con Moodle", record.name
                )
        return res

    def action_sync_moodle_retiro(self):
        """Busca al estudiante en Moodle por su username y suspende su
        MATRÍCULA en el curso (queda 'Suspendido' en el curso, pero
        puede seguir iniciando sesión y accediendo a otros cursos)."""
        client = self.env['moodle.client']
        config = self.env['moodle.config'].get_active_config()

        for record in self:
            student_code = record.student_code or record.student_id.student_code
            if not student_code:
                raise UserError(_(
                    "El estudiante no tiene código, no se puede ubicar en Moodle."
                ))

            user = client.get_user_by_field(
                'username', student_code, config=config, related_record=record
            )
            if not user:
                raise UserError(_(
                    "No se encontró en Moodle un usuario con username '%s'."
                ) % student_code)
            moodle_user_id = user.get('id')

            # ---------- Ubicar el curso ----------
            course_id = record.ri_id.moodle_course_id or False
            if not course_id:
                code_moodle = record.standard_id.subject_id.code_moodle
                course = (
                    client.search_course_by_shortname(
                        code_moodle, config=config, related_record=record
                    )
                    if code_moodle else None
                )
                course_id = course.get('id') if course else False

            if not course_id:
                raise UserError(_(
                    "No se pudo ubicar el curso en Moodle para la sección "
                    "'%s' (falta 'Código Moodle' en el curso)."
                ) % record.standard_id.display_name)

            # ---------- Fechas de la matrícula (misma fórmula que usa la
            #            inscripción; no se recalcula aparte) ----------
            timestart, timeend = record.ri_id._get_moodle_enrol_dates()

            # ---------- Suspender la MATRÍCULA (no la cuenta) ----------
            client.set_enrolment_suspended(
                moodle_user_id, course_id, timestart, timeend,
                role_id=config.enrol_role_id, suspended=True,
                config=config, related_record=record,
            )

            record.moodle_suspended = True
            record.moodle_sync_error = False
            record.moodle_error_message = False
            # La inscripción asociada también queda marcada como
            # suspendida: su 'plataforma_estado' pasa a "Suspendido" al
            # instante, sin esperar a que llegue su fecha de vencimiento.
            record.ri_id.moodle_suspended = True
            _logger.info(
                "Matrícula Moodle suspendida por retiro: %s (usuario %s, curso %s)",
                record.name, student_code, course_id,
            )

        return True

    # ------------------------------------------------------------------
    # Reintento manual desde el botón del formulario
    # ------------------------------------------------------------------
    def action_retry_sync_moodle(self):
        self.ensure_one()
        try:
            self.action_sync_moodle_retiro()
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
                'message': _('La matrícula del estudiante quedó suspendida en el curso de Moodle.'),
                'type': 'success',
                'sticky': False,
            },
        }
