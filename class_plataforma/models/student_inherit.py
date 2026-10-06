# See LICENSE file for full copyright and licensing details.

import calendar
import logging
from datetime import datetime

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

# Campos cuyo cambio dispara una actualización en Moodle (si el
# estudiante ya estaba sincronizado). 'name'/'email'/'login' llegan aquí
# gracias a la delegación de student.student sobre res.users.
_MOODLE_WATCHED_FIELDS = {'name', 'last', 'middle', 'email', 'login'}


class StudentStudentMoodle(models.Model):
    """Integración con Moodle sobre student.student.

    A diferencia de Inscripción/Retiro/Cambio, aquí NO se toca matrícula
    ni grupo — solo la cuenta del usuario (crear/actualizar datos
    básicos) y una consulta de estado bajo demanda. El 'username' en
    Moodle es siempre student_code, igual que en el resto del módulo.
    """

    _inherit = 'student.student'

    moodle_synced = fields.Boolean(
        string='Sincronizado con la Plataforma', default=False, copy=False,
        help="Indica si ya existe (o se intentó crear/actualizar) el "
             "usuario de este estudiante en la Plataforma.",
    )
    moodle_user_id = fields.Integer(
        string='ID de usuario en la Plataforma', copy=False,
        help="Cache del ID de usuario en la Plataforma.",
    )
    moodle_sync_error = fields.Boolean(
        string='Error en sincronización', default=False, copy=False,
    )
    moodle_error_message = fields.Text(
        string='Mensaje de error', readonly=True, copy=False,
    )
    moodle_status_snapshot = fields.Text(
        string='Último estado consultado', readonly=True, copy=False,
        help="Resultado de la última vez que se consultó el estado en "
             "la Plataforma. No se actualiza solo, es una foto del "
             "momento en que se consultó.",
    )
    moodle_sync_log_ids = fields.One2many(
        'moodle.sync.log', 'student_id',
        string='Log de sincronización',
        readonly=True,
    )

    # ---- Campos visibles en la pestaña "Plataforma" del formulario ----
    plataforma_usuario = fields.Char(
        string='Usuario', related='student_code', readonly=True,
        help="Usuario con el que el estudiante accede a la Plataforma "
             "(es el mismo Código del estudiante).",
    )
    plataforma_curso = fields.Text(
        string='Curso(s) inscrito(s)', readonly=True, copy=False,
        help="Cursos en los que el estudiante aparece matriculado en la "
             "Plataforma, según la última consulta.",
    )
    plataforma_estado = fields.Selection(
        [('activo', 'Activo'), ('suspendido', 'Suspendido')],
        string='Estado', readonly=True, copy=False,
        help="Estado de la cuenta del estudiante en la Plataforma, "
             "según la última consulta.",
    )
    plataforma_fecha_vencimiento = fields.Datetime(
        string='Fecha de vencimiento en Plataforma',
        compute='_compute_plataforma_fecha_vencimiento',
        help="Hasta cuándo tiene acceso el estudiante según Odoo: la fecha "
             "de vencimiento más lejana entre sus inscripciones "
             "sincronizadas con la Plataforma.",
    )

    def _compute_plataforma_fecha_vencimiento(self):
        Inscripcion = self.env['student.inscripcion']
        for rec in self:
            sid = rec._origin.id
            insc = sid and Inscripcion.search([
                ('student_id', '=', sid),
                ('moodle_enrolled', '=', True),
                ('moodle_timeend', '!=', False),
            ], order='moodle_timeend desc', limit=1)
            rec.plataforma_fecha_vencimiento = (
                insc.moodle_timeend if insc else False
            )

    # ------------------------------------------------------------------
    # Hooks: crear al confirmar admisión, actualizar si cambian datos
    # ------------------------------------------------------------------
    def admission_done(self):
        # super() es quien genera student_code (nuestro username en
        # la Plataforma) — hay que llamarlo primero.
        res = super().admission_done()
        for record in self:
            try:
                record.action_sync_moodle_estudiante()
            except Exception as e:
                record.moodle_sync_error = True
                record.moodle_error_message = str(e)
                record.message_post(
                    body=_("Error al sincronizar con la Plataforma: %s") % e
                )
                _logger.exception(
                    "Error al sincronizar estudiante %s con la Plataforma",
                    record.display_name,
                )
        return res

    def write(self, vals):
        res = super().write(vals)
        if _MOODLE_WATCHED_FIELDS.intersection(vals.keys()):
            for record in self:
                if record.moodle_synced:
                    try:
                        record.action_sync_moodle_estudiante()
                    except Exception as e:
                        record.moodle_sync_error = True
                        record.moodle_error_message = str(e)
                        record.message_post(
                            body=_("Error al sincronizar con la Plataforma: %s") % e
                        )
                        _logger.exception(
                            "Error al sincronizar estudiante %s con la "
                            "Plataforma (actualización)", record.display_name,
                        )
        return res

    # ------------------------------------------------------------------
    # Helper: refresca curso(s), estado y fecha de vencimiento a partir
    # de un usuario ya ubicado en la Plataforma.
    # ------------------------------------------------------------------
    def _refresh_plataforma_status(self, client, config, moodle_user_id, account_suspended=None):
        self.ensure_one()
        courses = client.get_user_courses(
            moodle_user_id, config=config, related_record=self
        ) or []
        course_names = [c.get('fullname') or c.get('shortname') for c in courses]
        self.plataforma_curso = "\n".join(course_names) if course_names else False

        # El vencimiento ya no se lee de Moodle: se calcula desde Odoo
        # (plataforma_fecha_vencimiento) y aquí solo se devuelven los
        # cursos crudos para poder compararlo (ver _comparar_vencimiento).
        if account_suspended is not None:
            self.plataforma_estado = 'suspendido' if account_suspended else 'activo'

        return course_names, courses

    # ------------------------------------------------------------------
    # Comparación del vencimiento Odoo vs. Plataforma
    # ------------------------------------------------------------------
    def _fmt_dt(self, dt):
        return fields.Datetime.context_timestamp(self, dt).strftime('%d/%m/%Y %H:%M')

    def _comparar_vencimiento(self, courses):
        """Compara el vencimiento de Odoo con el de la Plataforma.

        Devuelve (lineas_de_texto, hay_diferencia). Si la Plataforma no
        devuelve 'timeend' para un curso, lo indica explícitamente en vez
        de dar un falso "correcto".
        """
        self.ensure_one()
        inscripciones = self.env['student.inscripcion'].search([
            ('student_id', '=', self.id),
            ('moodle_enrolled', '=', True),
            ('moodle_timeend', '!=', False),
        ])
        if not inscripciones:
            return [_("Odoo no tiene fecha de vencimiento registrada.")], False

        # Por curso, la inscripción con vencimiento más lejano
        esperado = {}
        for insc in inscripciones:
            cid = insc.moodle_course_id
            if cid and (cid not in esperado
                        or insc.moodle_timeend > esperado[cid].moodle_timeend):
                esperado[cid] = insc

        moodle = {c.get('id'): c.get('timeend') for c in courses}
        lineas, hay_diferencia = [], False
        for cid, insc in esperado.items():
            curso = insc.standard_id.subject_id.name or str(cid)
            exp_dt = insc.moodle_timeend
            exp_ts = calendar.timegm(exp_dt.timetuple())
            if cid not in moodle:
                hay_diferencia = True
                lineas.append(_("%s: no aparece matriculado en la Plataforma.") % curso)
                continue
            m_ts = moodle[cid]
            if m_ts is None:
                lineas.append(_(
                    "%s: la Plataforma no devolvió la fecha de vencimiento; "
                    "no se pudo comparar."
                ) % curso)
            elif int(m_ts) == exp_ts:
                lineas.append(_("%s: vencimiento correcto (%s).") % (curso, self._fmt_dt(exp_dt)))
            else:
                hay_diferencia = True
                m_txt = (self._fmt_dt(datetime.utcfromtimestamp(m_ts))
                         if m_ts else _("sin vencimiento"))
                lineas.append(_(
                    "%s: DIFERENCIA. Odoo: %s, Plataforma: %s."
                ) % (curso, self._fmt_dt(exp_dt), m_txt))
        return lineas, hay_diferencia

    # ------------------------------------------------------------------
    # Orquestación: crea el usuario si no existe, o actualiza si ya existe
    # ------------------------------------------------------------------
    def action_sync_moodle_estudiante(self):
        client = self.env['moodle.client']
        config = self.env['moodle.config'].get_active_config()

        for record in self:
            if not record.student_code:
                raise UserError(_(
                    "El estudiante no tiene 'Código' asignado todavía "
                    "(se genera al confirmar la admisión); no se puede "
                    "sincronizar con la Plataforma."
                ))

            username = record.student_code
            full_name = record.name or record.student_name or "Estudiante"
            parts = full_name.strip().split()
            n = len(parts)
            if n <= 1:
                first_name, last_name = full_name, full_name
            elif n == 2:
                first_name, last_name = parts[0], parts[1]
            elif n == 3:
                first_name, last_name = f"{parts[0]} {parts[1]}", parts[2]
            else:
                first_name, last_name = f"{parts[0]} {parts[1]}", " ".join(parts[2:])

            firstname = f"{username} {first_name}" if first_name else username
            lastname = last_name

            email = record.email
            if not email and record.user_id and record.user_id.partner_id:
                email = record.user_id.partner_id.email
            if not email:
                email = f"{username}@cursoscleveland.com"

            user = client.get_user_by_field(
                'username', username, config=config, related_record=record
            )
            if not user:
                user = client.get_user_by_field(
                    'email', email, config=config, related_record=record
                )

            user_vals = {
                'email': email,
                'firstname': firstname,
                'lastname': lastname,
                'city': config.default_city,
                'country': config.default_country,
            }

            if user:
                moodle_user_id = user.get('id')
                client.update_user(
                    {**user_vals, 'id': moodle_user_id},
                    config=config, related_record=record,
                )
                account_suspended = bool(user.get('suspended'))
            else:
                create_vals = dict(user_vals)
                create_vals.update({
                    'username': username,
                    'auth': 'manual',
                    'password': config.default_password,
                })
                moodle_user_id = client.create_user(
                    create_vals, config=config, related_record=record,
                )
                account_suspended = False

            if not moodle_user_id:
                raise UserError(_(
                    "No se pudo obtener ni generar el ID del usuario en la Plataforma."
                ))

            record.moodle_user_id = moodle_user_id
            record.moodle_synced = True
            record.moodle_sync_error = False
            record.moodle_error_message = False
            record._refresh_plataforma_status(
                client, config, moodle_user_id, account_suspended=account_suspended
            )
            _logger.info(
                "Usuario de Plataforma sincronizado para estudiante %s (username %s)",
                record.display_name, username,
            )

        return True

    # ------------------------------------------------------------------
    # Botón: verificar estado actual en la Plataforma (consulta en vivo)
    # ------------------------------------------------------------------
    def action_check_moodle_status(self):
        self.ensure_one()
        client = self.env['moodle.client']
        config = self.env['moodle.config'].get_active_config()

        if not self.student_code:
            raise UserError(_(
                "El estudiante no tiene 'Código' asignado todavía."
            ))

        user = client.get_user_by_field(
            'username', self.student_code, config=config, related_record=self
        )
        if not user:
            self.moodle_status_snapshot = _(
                "No existe un usuario en la Plataforma con username '%s'."
            ) % self.student_code
            self.plataforma_curso = False
            self.plataforma_estado = False
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No encontrado en la Plataforma'),
                    'message': self.moodle_status_snapshot,
                    'type': 'warning',
                    'sticky': True,
                },
            }

        moodle_user_id = user.get('id')
        account_suspended = bool(user.get('suspended'))
        self.moodle_user_id = moodle_user_id
        course_names, courses = self._refresh_plataforma_status(
            client, config, moodle_user_id, account_suspended=account_suspended
        )
        lineas, hay_diferencia = self._comparar_vencimiento(courses)

        status_txt = _('Suspendida') if account_suspended else _('Activa')
        courses_txt = ", ".join(course_names) if course_names else _('ninguno')
        venc_txt = ''
        if self.plataforma_fecha_vencimiento:
            venc_txt = _("\nVencimiento (Odoo): %s") % self._fmt_dt(
                self.plataforma_fecha_vencimiento)
        cmp_txt = ("\n" + "\n".join(lineas)) if lineas else ''

        self.moodle_status_snapshot = _(
            "Cuenta: %s\nCursos matriculados: %s%s%s"
        ) % (status_txt, courses_txt, venc_txt, cmp_txt)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Estado en la Plataforma'),
                'message': self.moodle_status_snapshot,
                'type': 'warning' if hay_diferencia else 'success',
                'sticky': True,
            },
        }

    # ------------------------------------------------------------------
    # Reintento manual desde el botón del formulario
    # ------------------------------------------------------------------
    def action_retry_sync_moodle(self):
        self.ensure_one()
        try:
            self.action_sync_moodle_estudiante()
        except Exception as e:
            self.moodle_sync_error = True
            self.moodle_error_message = str(e)
            self.message_post(
                body=_("Error al sincronizar con la Plataforma: %s") % e
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error al sincronizar'),
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
                'message': _('El usuario del estudiante quedó sincronizado con la Plataforma.'),
                'type': 'success',
                'sticky': False,
            },
        }
