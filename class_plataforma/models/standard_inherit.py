# See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

# Si cambia alguno de estos campos de la sección, los IDs de curso y grupo
# guardados de la Plataforma dejan de ser válidos.
_MOODLE_CACHE_KEYS = {'code', 'subject_id'}


class SchoolStandardMoodle(models.Model):
    """Integración con Moodle sobre school.standard (Secciones).

    La sincronización compara, no repite:
      1. Ubica el grupo de la sección (usa los IDs guardados; solo busca o
         crea el grupo en la Plataforma la primera vez, o si dejaron de servir).
      2. Pide los integrantes actuales del grupo (1 petición).
      3. Compara contra los estudiantes inscritos en Odoo y solo agrega al
         grupo a los que faltan (matriculándolos antes si hace falta).
      4. Guarda el resultado: la próxima vez solo se comparan integrantes.

    Para no buscar estudiantes uno por uno, cada estudiante de Odoo debe estar
    vinculado a su usuario de la Plataforma (moodle_user_id). Los que aún no
    lo están se ubican todos juntos y quedan vinculados para siempre.
    """

    _inherit = 'school.standard'

    moodle_course_id = fields.Integer(
        string='ID de curso en Moodle',
        readonly=True, copy=False,
        help="Cache del ID de curso en Moodle, obtenido en la última "
             "sincronización de esta sección.",
    )
    moodle_course_name = fields.Char(
        string='Nombre del curso en Plataforma',
        readonly=True, copy=False,
        help="Cache del nombre del curso en la Plataforma.",
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
    # Invalidar los IDs guardados si cambia el código o el curso
    # ------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if _MOODLE_CACHE_KEYS.intersection(vals):
            super().write({
                'moodle_course_id': 0,
                'moodle_course_name': False,
                'moodle_group_id': 0,
                'moodle_group_synced': False,
            })
        return res

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
    # Paso 1: ubicar curso y grupo (con IDs guardados cuando se puede)
    # ------------------------------------------------------------------
    def _moodle_resolve_group(self, client, config, force=False):
        """Devuelve (course_id, course_name, group_id, mensaje, desde_cache).

        Con los IDs guardados no hace ninguna petición. Si falta alguno (o
        force=True, porque los guardados fallaron) los busca en la Plataforma
        y crea el grupo si no existe.
        """
        self.ensure_one()
        group_name = self.code
        code_moodle = self.subject_id.code_moodle

        if not force and self.moodle_course_id and self.moodle_group_id:
            return (
                self.moodle_course_id,
                self.moodle_course_name or code_moodle,
                self.moodle_group_id,
                _("Grupo '%s' (ID: %s): se usaron los datos guardados.")
                % (group_name, self.moodle_group_id),
                True,
            )

        course_id = False if force else self.moodle_course_id
        course_name = self.moodle_course_name or code_moodle
        if not course_id:
            course = client.search_course_by_shortname(
                code_moodle, config=config, related_record=self
            )
            if not course:
                raise UserError(_(
                    "No se encontró en la Plataforma un curso con el código '%s'."
                ) % code_moodle)
            course_id = course.get('id')
            course_name = course.get('fullname') or course.get('shortname') or code_moodle

        groups = client.get_course_groups(
            course_id, config=config, related_record=self
        ) or []
        match = next((g for g in groups if g.get('name') == group_name), None)
        if match:
            group_id = match.get('id')
            msg = _("Grupo '%s' verificado en la Plataforma (ID: %s).") % (group_name, group_id)
        else:
            group_id = client.create_group(
                course_id, group_name, config=config, related_record=self
            )
            if not group_id:
                raise UserError(_(
                    "No se pudo crear el grupo '%s' en la Plataforma."
                ) % group_name)
            msg = _("Grupo '%s' creado en la Plataforma (ID: %s).") % (group_name, group_id)

        self.write({
            'moodle_course_id': course_id,
            'moodle_course_name': course_name,
            'moodle_group_id': group_id,
        })
        return course_id, course_name, group_id, msg, False

    # ------------------------------------------------------------------
    # Paso 2: vincular estudiantes con su usuario de la Plataforma
    # ------------------------------------------------------------------
    def _moodle_link_students(self, client, config, inscriptions):
        """Devuelve (filas, errores). Cada fila es un dict con la inscripción,
        el estudiante, su código, nombre y 'uid' (ID de usuario en la
        Plataforma). Los que ya tienen ID guardado no cuestan ninguna
        petición; los demás se buscan TODOS JUNTOS (1 petición por username
        y, solo para los que sigan sin aparecer, 1 más por email).
        """
        self.ensure_one()
        rows, errors, pending = [], [], []

        for insc in inscriptions:
            student = insc.student_id
            code = student.student_code or insc.student_code
            name = (student.name or student.student_name
                    or insc.student_partner_id.name or _("Estudiante"))
            if not code:
                errors.append((name, '', _("no tiene código de estudiante")))
                continue
            uid = student.moodle_user_id or insc.moodle_user_id
            row = {'insc': insc, 'student': student, 'code': code,
                   'name': name, 'uid': uid, 'done': False}
            if uid:
                if not student.moodle_user_id:
                    student.write({'moodle_user_id': uid, 'moodle_synced': True})
                rows.append(row)
            else:
                pending.append(row)

        if not pending:
            return rows, errors

        assigned = {r['uid'] for r in rows}

        def link(row, uid):
            row['done'] = True
            if uid in assigned:
                errors.append((row['name'], row['code'], _(
                    "la cuenta de la Plataforma (ID %s) ya está vinculada a "
                    "otro estudiante") % uid))
                return
            assigned.add(uid)
            row['uid'] = uid
            row['student'].write({'moodle_user_id': uid, 'moodle_synced': True})
            if not row['insc'].moodle_user_id:
                row['insc'].moodle_user_id = uid
            rows.append(row)

        # 2a. Todos por username (el username es el código del estudiante)
        found = client.get_users_by_field(
            'username', [r['code'] for r in pending],
            config=config, related_record=self,
        )
        by_username = {(u.get('username') or '').lower(): u for u in found}
        for row in pending:
            user = by_username.get(row['code'].lower())
            if user:
                link(row, user['id'])

        # 2b. Los que siguen sin aparecer, todos juntos por email
        left = [r for r in pending if not r['done']]
        if left:
            by_email_rows = {}
            for row in left:
                email = (row['insc']._get_moodle_email() or '').lower()
                by_email_rows.setdefault(email, []).append(row)
            found = client.get_users_by_field(
                'email', list(by_email_rows),
                config=config, related_record=self,
            )
            by_email_users = {}
            for user in found:
                by_email_users.setdefault((user.get('email') or '').lower(), []).append(user)
            for email, email_rows in by_email_rows.items():
                users = by_email_users.get(email, [])
                if len(email_rows) == 1 and len(users) == 1:
                    link(email_rows[0], users[0]['id'])
                elif users:
                    for row in email_rows:
                        row['done'] = True
                        errors.append((row['name'], row['code'], _(
                            "el correo '%s' coincide con varias cuentas o "
                            "estudiantes; no se vinculó automáticamente") % email))

        for row in pending:
            if not row['done']:
                errors.append((row['name'], row['code'], _(
                    "no existe en la Plataforma; sincronice primero al "
                    "estudiante")))
        return rows, errors

    # ------------------------------------------------------------------
    # Orquestación: comparar integrantes y agregar solo a los que faltan
    # ------------------------------------------------------------------
    def action_sync_moodle_seccion(self):
        """Sincroniza la sección con su grupo de la Plataforma.

        Con los IDs guardados y los estudiantes ya vinculados, una
        sincronización sin novedades cuesta UNA petición (consultar los
        integrantes del grupo).
        """
        client = self.env['moodle.client']
        config = self.env['moodle.config'].get_active_config()

        for record in self:
            if not record.code:
                raise UserError(_(
                    "La sección no tiene configurado un 'Código'. Por favor "
                    "asígnele un código a la sección antes de sincronizar con la Plataforma."
                ))
            if not record.subject_id.code_moodle:
                raise UserError(_(
                    "El curso '%s' no tiene configurado un 'Código Moodle'. "
                    "Configure el código en el catálogo de Cursos."
                ) % record.subject_id.name)

            # ---- 1. Curso y grupo ----
            course_id, course_name, group_id, group_msg, from_cache = \
                record._moodle_resolve_group(client, config)

            # Integrantes: SOLO inscripciones confirmadas (done). Sin
            # fallback a otros estados: no se debe matricular a borradores
            # ni volver a meter en el grupo a retirados.
            inscriptions = record.student_ids.filtered(lambda s: s.state == 'done')
            if not inscriptions:
                record.write({
                    'moodle_group_synced': True,
                    'moodle_sync_error': False,
                    'moodle_error_message': False,
                    'moodle_last_sync': fields.Datetime.now(),
                    'moodle_members_count': 0,
                    'moodle_sync_status': group_msg + "\n" + _(
                        "La sección no contiene estudiantes activos para "
                        "inscribir en el grupo."),
                })
                continue

            # ---- 2. Integrantes actuales del grupo (1 petición) ----
            try:
                members = client.get_group_members(
                    group_id, config=config, related_record=record
                )
            except UserError:
                if not from_cache:
                    raise
                # Los IDs guardados ya no sirven (p. ej. borraron el grupo):
                # se vuelve a ubicar todo una vez y se reintenta.
                course_id, course_name, group_id, group_msg, from_cache = \
                    record._moodle_resolve_group(client, config, force=True)
                members = client.get_group_members(
                    group_id, config=config, related_record=record
                )

            # ---- 3. Vincular estudiantes con su usuario de la Plataforma ----
            rows, link_errors = record._moodle_link_students(
                client, config, inscriptions
            )

            # ---- 4. Comparar: ¿quién ya está y quién falta? ----
            already = [r for r in rows if r['uid'] in members]
            missing = [r for r in rows if r['uid'] not in members]
            call_errors = []   # [(fila, mensaje)] errores al hablar con la Plataforma

            # ---- 5. Matricular (en lote) a los que faltan y no están matriculados ----
            to_enrol = [
                r for r in missing
                if not r['insc'].moodle_enrolled
                or r['insc'].moodle_course_id != course_id
            ]
            for row in to_enrol:
                row['timestart'], row['timeend'] = row['insc']._get_moodle_enrol_dates()
            if to_enrol:
                enrolled = to_enrol
                try:
                    client.enrol_users(
                        [{'user_id': r['uid'], 'course_id': course_id,
                          'timestart': r['timestart'], 'timeend': r['timeend']}
                         for r in to_enrol],
                        config=config, related_record=record,
                    )
                except UserError:
                    # El lote es atómico: si uno falla, ninguno se matricula.
                    # Se repite uno por uno para saber exactamente cuál falla.
                    enrolled = []
                    for row in to_enrol:
                        try:
                            client.enrol_user(
                                row['uid'], course_id, row['timestart'], row['timeend'],
                                role_id=config.enrol_role_id, config=config,
                                related_record=record, student_code=row['code'],
                            )
                            enrolled.append(row)
                        except UserError as e:
                            call_errors.append((row, str(e)))
                for row in enrolled:
                    row['insc'].write({
                        'moodle_enrolled': True,
                        'moodle_course_id': course_id,
                        'moodle_timeend': datetime.utcfromtimestamp(row['timeend']),
                        'moodle_user_id': row['uid'],
                        'plataforma_curso': course_name,
                        'moodle_suspended': False,
                        'moodle_sync_error': False,
                        'moodle_error_message': False,
                    })

            # ---- 6. Agregar al grupo (en lote) a los que faltan ----
            failed_uids = {r['uid'] for r, _msg in call_errors}
            to_add = [r for r in missing if r['uid'] not in failed_uids]
            added = []
            if to_add:
                try:
                    client.add_group_members(
                        group_id, [r['uid'] for r in to_add],
                        config=config, related_record=record,
                    )
                    added = to_add
                except UserError:
                    for row in to_add:
                        try:
                            client.add_group_members(
                                group_id, row['uid'], config=config,
                                related_record=record, student_code=row['code'],
                            )
                            added.append(row)
                        except UserError as e:
                            call_errors.append((row, str(e)))

            # ---- 7. Guardar el resultado ----
            synced_count = len(already) + len(added)
            failed_count = len(link_errors) + len(call_errors)

            lines = [
                group_msg,
                _("Integrantes en el grupo antes de sincronizar: %s") % len(members),
                _("Estudiantes inscritos en Odoo: %s") % len(inscriptions),
            ]
            if already:
                lines.append(_("• Ya estaban en el grupo: %s") % len(already))
            if added:
                lines.append(_("• Agregados ahora: %s") % len(added))
                for row in added:
                    lines.append("    - %s (%s)" % (row['name'], row['code']))
            if failed_count:
                lines.append(_("• Con error: %s") % failed_count)
                for name, code, reason in link_errors:
                    lines.append("    - %s%s: %s" % (
                        name, " (%s)" % code if code else "", reason))
                for row, msg in call_errors:
                    lines.append("    - %s (%s): %s" % (row['name'], row['code'], msg))

            # Si falló algo hablando con la Plataforma y se usaron IDs
            # guardados, se descartan para que el próximo intento los
            # vuelva a buscar (por si el grupo o el curso cambiaron).
            if from_cache and call_errors:
                record.write({'moodle_course_id': 0, 'moodle_group_id': 0})
                lines.append(_(
                    "Se descartaron los datos guardados del grupo; el "
                    "próximo intento los volverá a buscar."))

            record.write({
                'moodle_group_synced': not failed_count,
                'moodle_sync_error': bool(failed_count),
                'moodle_error_message': (
                    _("%s estudiante(s) con error. Revise el 'Detalle de "
                      "sincronización'.") % failed_count
                ) if failed_count else False,
                'moodle_last_sync': fields.Datetime.now(),
                'moodle_members_count': synced_count,
                'moodle_sync_status': "\n".join(lines),
            })
            _logger.info(
                "Sincronización de sección %s: grupo %s, %s ya estaban, %s agregados, %s con error.",
                record.code, group_id, len(already), len(added), failed_count,
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
