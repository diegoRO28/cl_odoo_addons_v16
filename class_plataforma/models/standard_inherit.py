# See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class SchoolStandardMoodle(models.Model):
    """Integración con Moodle sobre school.standard (Secciones).

    Permite sincronizar las secciones de Class con grupos de Moodle:
    - Realiza una única petición para buscar grupos en el curso correspondiente.
    - Si el grupo existe, usa su ID; si no existe, crea el grupo.
    - Asegura que cada integrante de la sección esté vinculado con su usuario
      en Moodle (moodle_user_id), matriculado en el curso, e inscrito en el grupo.
    - Mantiene trazabilidad en moodle.sync.log vinculada a la sección.
    """

    _inherit = 'school.standard'

    moodle_course_id = fields.Integer(
        string='ID de curso en Moodle',
        readonly=True, copy=False,
        help="Cache del ID de curso en Moodle, obtenido en la última "
             "sincronización de esta sección.",
    )
    moodle_group_id = fields.Integer(
        string='ID de grupo en Plataforma',
        readonly=True, copy=False,
        help="ID del grupo correspondiente a esta sección en la Plataforma Moodle.",
    )
    moodle_group_synced = fields.Boolean(
        string='Grupo sincronizado en Plataforma',
        default=False, copy=False,
        help="Indica si el grupo y sus integrantes ya fueron sincronizados en la Plataforma.",
    )
    moodle_sync_error = fields.Boolean(
        string='Error en sincronización',
        default=False, copy=False,
    )
    moodle_error_message = fields.Text(
        string='Mensaje de error Plataforma',
        readonly=True, copy=False,
    )
    moodle_last_sync = fields.Datetime(
        string='Última sincronización',
        readonly=True, copy=False,
        help="Fecha y hora de la última sincronización con la Plataforma.",
    )
    moodle_sync_status = fields.Text(
        string='Detalle de sincronización',
        readonly=True, copy=False,
        help="Resumen informativo del resultado de la última sincronización.",
    )
    moodle_members_count = fields.Integer(
        string='Integrantes sincronizados',
        readonly=True, copy=False,
        help="Cantidad de estudiantes confirmados en el grupo de la Plataforma.",
    )
    moodle_sync_log_ids = fields.One2many(
        'moodle.sync.log', 'standard_id',
        string='Log de sincronización',
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Hook: confirmación de sección (INICIAR SECCIÓN)
    # ------------------------------------------------------------------
    def set_done(self):
        res = super().set_done()
        for record in self:
            try:
                record.action_sync_moodle_seccion()
            except Exception as e:
                record.moodle_sync_error = True
                record.moodle_error_message = str(e)
                record.message_post(
                    body=_("Error al sincronizar grupo con la Plataforma: %s") % e
                )
                _logger.exception(
                    "Error al sincronizar sección %s con la Plataforma",
                    record.display_name,
                )
        return res

    # ------------------------------------------------------------------
    # Orquestación de sincronización de sección a grupo de Moodle
    # ------------------------------------------------------------------
    def action_sync_moodle_seccion(self):
        """Sincroniza la sección con la Plataforma Moodle.
        1. Valida el código de sección y el código Moodle del curso.
        2. Realiza UNA SOLA petición para consultar los grupos del curso en Moodle.
        3. Si el grupo existe, toma su ID; si no existe, lo crea.
        4. Para cada integrante activo de la sección:
           - Asegura la vinculación con su usuario Moodle (moodle_user_id).
           - Asegura que esté matriculado en el curso.
           - Inscribe al usuario en el grupo de Moodle.
        5. Actualiza campos informativos y audita en moodle.sync.log.
        """
        client = self.env['moodle.client']
        config = self.env['moodle.config'].get_active_config()

        for record in self:
            group_name = record.code
            if not group_name:
                raise UserError(_(
                    "La sección no tiene configurado un 'Código'. Por favor "
                    "asígnele un código a la sección antes de sincronizar con la Plataforma."
                ))

            # Resolver código Moodle del curso
            code_moodle = record.subject_id.code_moodle
            if not code_moodle:
                raise UserError(_(
                    "El curso '%s' no tiene configurado un 'Código Moodle'. "
                    "Configure el código en el catálogo de Cursos."
                ) % record.subject_id.name)

            # Buscar curso en Moodle
            course = client.search_course_by_shortname(
                code_moodle, config=config, related_record=record
            )
            if not course:
                raise UserError(_(
                    "No se encontró en la Plataforma un curso con el código '%s'."
                ) % code_moodle)

            moodle_course_id = course.get('id')
            course_name = course.get('fullname') or course.get('shortname') or code_moodle
            record.moodle_course_id = moodle_course_id

            # UNA SOLA petición para buscar grupos en el curso
            groups = client.get_course_groups(
                moodle_course_id, config=config, related_record=record
            ) or []

            group_match = next((g for g in groups if g.get('name') == group_name), None)
            if group_match:
                group_id = group_match.get('id')
                group_action_msg = _("Grupo '%s' verificado en Plataforma (ID: %s)") % (group_name, group_id)
            else:
                group_id = client.create_group(
                    moodle_course_id, group_name, config=config, related_record=record
                )
                if not group_id:
                    raise UserError(_(
                        "No se pudo crear el grupo '%s' en la Plataforma."
                    ) % group_name)
                group_action_msg = _("Grupo '%s' creado exitosamente en Plataforma (ID: %s)") % (group_name, group_id)

            record.moodle_group_id = group_id

            # Integrantes de la sección: SOLO inscripciones confirmadas
            # (done). Sin fallback a otros estados: no se debe matricular
            # a borradores ni volver a meter en el grupo a retirados.
            active_inscriptions = record.student_ids.filtered(
                lambda s: s.state == 'done'
            )

            if not active_inscriptions:
                record.write({
                    'moodle_group_synced': True,
                    'moodle_sync_error': False,
                    'moodle_error_message': False,
                    'moodle_last_sync': fields.Datetime.now(),
                    'moodle_members_count': 0,
                    'moodle_sync_status': f"{group_action_msg}\n" + _("La sección no contiene estudiantes activos para inscribir en el grupo."),
                })
                continue

            synced_count = 0
            failed_count = 0
            status_lines = [group_action_msg]

            for inscrip in active_inscriptions:
                student = inscrip.student_id
                student_code = student.student_code or inscrip.student_code
                student_name = student.name or student.student_name or inscrip.student_partner_id.name or _("Estudiante")

                if not student_code:
                    _logger.warning("Estudiante %s (ID %s) no tiene código asignado, omitiendo.", student_name, student.id)
                    failed_count += 1
                    status_lines.append(_("• %s: Omitido (sin código de estudiante)") % student_name)
                    continue

                try:
                    # 1. Asegurar vinculación del estudiante en Odoo con Moodle (moodle_user_id)
                    moodle_user_id = student.moodle_user_id
                    if not moodle_user_id:
                        moodle_user = client.get_user_by_field(
                            'username', student_code, config=config,
                            related_record=record, student_code=student_code
                        )
                        if not moodle_user:
                            email = inscrip._get_moodle_email()
                            moodle_user = client.get_user_by_field(
                                'email', email, config=config,
                                related_record=record, student_code=student_code
                            )

                        if moodle_user:
                            moodle_user_id = moodle_user.get('id')
                            student.write({
                                'moodle_user_id': moodle_user_id,
                                'moodle_synced': True,
                            })
                        else:
                            student.action_sync_moodle_estudiante()
                            moodle_user_id = student.moodle_user_id

                    if not moodle_user_id:
                        failed_count += 1
                        status_lines.append(_("• %s (%s): Error - No se pudo vincular con usuario de Plataforma") % (student_name, student_code))
                        continue

                    # 2. Asegurar matrícula en el curso antes de agregar al grupo
                    if not inscrip.moodle_enrolled or inscrip.moodle_course_id != moodle_course_id:
                        timestart, timeend = inscrip._get_moodle_enrol_dates()

                        client.enrol_user(
                            moodle_user_id, moodle_course_id, timestart, timeend,
                            role_id=config.enrol_role_id, config=config,
                            related_record=record, student_code=student_code,
                        )
                        inscrip.write({
                            'moodle_enrolled': True,
                            'moodle_course_id': moodle_course_id,
                            'moodle_timeend': datetime.utcfromtimestamp(timeend),
                            'moodle_user_id': moodle_user_id,
                            'plataforma_curso': course_name,
                            'moodle_suspended': False,
                            'moodle_sync_error': False,
                            'moodle_error_message': False,
                        })

                    # 3. Inscribir usuario en el grupo de la sección
                    client.add_group_members(
                        group_id, moodle_user_id,
                        config=config, related_record=record, student_code=student_code,
                    )
                    synced_count += 1
                    status_lines.append(_("• %s (%s): Vinculado e inscrito en grupo") % (student_name, student_code))

                except Exception as e:
                    failed_count += 1
                    _logger.exception("Error al sincronizar estudiante %s en sección %s", student_code, record.code)
                    status_lines.append(_("• %s (%s): Error - %s") % (student_name, student_code, str(e)))

            record.write({
                'moodle_group_synced': not failed_count,
                'moodle_sync_error': bool(failed_count),
                'moodle_error_message': (
                    _("%s estudiante(s) con error. Revise el 'Detalle de "
                      "sincronización'.") % failed_count
                ) if failed_count else False,
                'moodle_last_sync': fields.Datetime.now(),
                'moodle_members_count': synced_count,
                'moodle_sync_status': "\n".join(status_lines),
            })
            _logger.info(
                "Sincronización de sección %s completada: grupo %s (ID %s), %s estudiantes inscritos.",
                record.code, group_name, group_id, synced_count,
            )

        return True

    # ------------------------------------------------------------------
    # Reintento / ejecución manual desde botón
    # ------------------------------------------------------------------
    def action_retry_sync_moodle(self):
        """Reintento manual desde el formulario de la sección.
        Atrapa excepciones para mostrar notificación en UI y no revertir
        los registros de auditoría de moodle.sync.log.
        """
        self.ensure_one()
        try:
            self.action_sync_moodle_seccion()
        except Exception as e:
            self.moodle_sync_error = True
            self.moodle_error_message = str(e)
            self.message_post(
                body=_("Error al sincronizar grupo con la Plataforma: %s") % e
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error al sincronizar con la Plataforma'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                },
            }
        if self.moodle_sync_error:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sincronización con errores'),
                    'message': self.moodle_error_message,
                    'type': 'warning',
                    'sticky': True,
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sincronización exitosa'),
                'message': _('El grupo y sus integrantes quedaron sincronizados con la Plataforma.'),
                'type': 'success',
                'sticky': False,
            },
        }
