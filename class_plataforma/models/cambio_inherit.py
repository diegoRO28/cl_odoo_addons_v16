# See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class StudentCambioMoodle(models.Model):
    """Integración con Moodle sobre student.cambio.

    Alcance (según lo pedido): NO se encarga de la matrícula a nivel de
    curso (eso ya lo cubre student.inscripcion — el propio
    genera_registro_inscripcion() de student.cambio crea y confirma una
    inscripción nueva en la sección destino, que dispara automáticamente
    el _inherit de Inscripción). Este módulo solo mueve al estudiante de
    GRUPO dentro de Moodle: lo saca del grupo de la sección origen y lo
    agrega al grupo de la sección destino.
    """

    _inherit = 'student.cambio'

    moodle_group_synced = fields.Boolean(
        string='Grupo Moodle sincronizado', default=False, copy=False,
    )
    moodle_sync_error = fields.Boolean(
        string='Error en sincronización', default=False, copy=False,
    )
    moodle_error_message = fields.Text(
        string='Mensaje de error Moodle', readonly=True, copy=False,
    )

    # ------------------------------------------------------------------
    # Hook: se dispara automáticamente al confirmar el cambio
    # ------------------------------------------------------------------
    def admission_done(self):
        # super() ya crea Y confirma la inscripción en la sección destino
        # (genera_registro_inscripcion -> record_inscrip.admission_done()),
        # lo cual dispara el _inherit de Inscripción y matricula al
        # estudiante en el curso destino si hace falta. Aquí solo falta
        # el movimiento de GRUPO dentro de Moodle.
        res = super().admission_done()
        for record in self:
            try:
                record.action_sync_moodle_grupo()
            except Exception as e:
                record.moodle_sync_error = True
                record.moodle_error_message = str(e)
                record.message_post(
                    body=_("Error al sincronizar grupo Moodle: %s") % e
                )
                _logger.exception(
                    "Error al sincronizar grupo Moodle para cambio %s", record.name
                )
        return res

    def action_sync_moodle_grupo(self):
        """Busca al estudiante en Moodle y lo mueve del grupo configurado
        en la sección origen al grupo configurado en la sección destino.
        El código de grupo es el campo 'code' que ya existe en
        school.standard (ej. 'SEC-02/BEG') — se usa tal cual, no hace
        falta un campo nuevo.

        Reutiliza los IDs de curso/grupo ya guardados en school.standard
        (los mismos que mantiene la sincronización de Sección) y el
        moodle_user_id ya vinculado al estudiante: con todo cacheado,
        esto cuesta ~2 peticiones (quitar + agregar del grupo) en vez de
        buscar usuario, curso y grupo de origen y destino cada vez."""
        client = self.env['moodle.client']
        config = self.env['moodle.config'].get_active_config()

        for record in self:
            student = record.student_id
            student_code = record.student_code or student.student_code
            if not student_code:
                raise UserError(_(
                    "El estudiante no tiene código, no se puede ubicar en Moodle."
                ))

            moodle_user_id = student.moodle_user_id or False
            if not moodle_user_id:
                user = client.get_user_by_field(
                    'username', student_code, config=config, related_record=record
                )
                if not user:
                    raise UserError(_(
                        "No se encontró en Moodle un usuario con username '%s'."
                    ) % student_code)
                moodle_user_id = user.get('id')
                if not student.moodle_user_id:
                    student.write({'moodle_user_id': moodle_user_id, 'moodle_synced': True})

            # ---------- Grupo ORIGEN (IDs ya guardados en la sección) ----------
            origin_standard = record.standard_id
            origin_group_code = origin_standard.code
            origin_group_id = origin_standard.moodle_group_id or False
            if not origin_group_id and origin_group_code:
                origin_code_moodle = origin_standard.subject_id.code_moodle
                if origin_code_moodle:
                    origin_course_id = origin_standard.moodle_course_id or False
                    if not origin_course_id:
                        origin_course = client.search_course_by_shortname(
                            origin_code_moodle, config=config, related_record=record
                        )
                        origin_course_id = origin_course.get('id') if origin_course else False
                        if origin_course_id:
                            origin_standard.moodle_course_id = origin_course_id
                    if origin_course_id:
                        origin_group_id = client.get_or_create_group(
                            origin_course_id, origin_group_code,
                            config=config, related_record=record,
                        )
                        origin_standard.moodle_group_id = origin_group_id

            # ---------- Grupo DESTINO (obligatorio; IDs ya guardados) ----------
            dest_standard = record.standard_des_id
            dest_group_code = dest_standard.code
            if not dest_group_code:
                raise UserError(_(
                    "La sección destino '%s' no tiene un 'code' asignado, "
                    "no se puede determinar el grupo en Moodle."
                ) % dest_standard.display_name)

            dest_course_id = dest_standard.moodle_course_id or False
            if not dest_course_id:
                dest_code_moodle = dest_standard.subject_id.code_moodle
                if not dest_code_moodle:
                    raise UserError(_(
                        "El curso de la sección destino '%s' no tiene 'Código "
                        "Moodle' configurado."
                    ) % dest_standard.subject_id.name)
                dest_course = client.search_course_by_shortname(
                    dest_code_moodle, config=config, related_record=record
                )
                if not dest_course:
                    raise UserError(_(
                        "No se encontró en Moodle el curso destino (Código "
                        "Moodle '%s')."
                    ) % dest_code_moodle)
                dest_course_id = dest_course.get('id')
                dest_standard.moodle_course_id = dest_course_id

            dest_group_id = dest_standard.moodle_group_id or False
            if not dest_group_id:
                dest_group_id = client.get_or_create_group(
                    dest_course_id, dest_group_code,
                    config=config, related_record=record,
                )
                dest_standard.moodle_group_id = dest_group_id

            # ---------- Ejecutar el movimiento ----------
            if origin_group_id:
                client.remove_group_members(
                    origin_group_id, moodle_user_id,
                    config=config, related_record=record,
                )
            client.add_group_members(
                dest_group_id, moodle_user_id,
                config=config, related_record=record,
            )

            record.moodle_group_synced = True
            record.moodle_sync_error = False
            record.moodle_error_message = False
            _logger.info(
                "Grupo Moodle sincronizado para cambio %s (usuario %s): "
                "%s -> %s", record.name, student_code,
                origin_group_code, dest_group_code,
            )

        return True

    # ------------------------------------------------------------------
    # Reintento manual desde el botón del formulario
    # ------------------------------------------------------------------
    def action_retry_sync_moodle(self):
        self.ensure_one()
        try:
            self.action_sync_moodle_grupo()
        except Exception as e:
            self.moodle_sync_error = True
            self.moodle_error_message = str(e)
            self.message_post(
                body=_("Error al sincronizar grupo Moodle: %s") % e
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
                'message': _('El estudiante quedó movido al grupo de la nueva sección.'),
                'type': 'success',
                'sticky': False,
            },
        }
