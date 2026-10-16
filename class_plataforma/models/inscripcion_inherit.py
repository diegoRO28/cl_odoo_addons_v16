# See LICENSE file for full copyright and licensing details.

import logging
import time
from datetime import datetime, timedelta

from odoo import api, fields, models
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
    moodle_timeend = fields.Datetime(
        string='Vencimiento en la Plataforma', readonly=True, copy=False,
        help="Fecha de vencimiento que Odoo envió a la Plataforma en la "
             "última sincronización de esta inscripción (UTC).",
    )
    moodle_user_id = fields.Integer(
        string='ID de usuario en la Plataforma', readonly=True, copy=False,
        help="ID del usuario del estudiante en la Plataforma, obtenido en "
             "la última sincronización de esta inscripción.",
    )

    # ---- Campos visibles en la sección "Plataforma" del formulario ----
    plataforma_usuario = fields.Char(
        string='Usuario', related='student_code', readonly=True,
        help="Usuario con el que el estudiante accede a la Plataforma "
             "(es el mismo Código del estudiante).",
    )
    plataforma_curso = fields.Char(
        string='Curso', readonly=True, copy=False,
        help="Curso de la Plataforma en el que quedó matriculado el "
             "estudiante en la última sincronización.",
    )
    moodle_suspended = fields.Boolean(
        string='Matrícula suspendida', readonly=True, copy=False,
        help="La matrícula fue suspendida de forma explícita (por ejemplo, "
             "por un Retiro), sin esperar a su fecha de vencimiento. Se "
             "limpia al volver a matricular.",
    )
    plataforma_estado = fields.Selection(
        [('activo', 'Activo'), ('suspendido', 'Suspendido')],
        string='Estado de la matrícula', compute='_compute_plataforma_estado',
        help="Estado de la matrícula en el curso de la Plataforma. Pasa a "
             "Suspendido cuando llega su fecha de vencimiento (o si fue "
             "suspendida explícitamente). Se calcula desde Odoo con la "
             "fecha que se envió a la Plataforma.",
    )

    @api.depends('moodle_enrolled', 'moodle_timeend', 'moodle_suspended')
    def _compute_plataforma_estado(self):
        now = fields.Datetime.now()
        for rec in self:
            if not rec.moodle_enrolled:
                rec.plataforma_estado = False
            elif rec.moodle_suspended or (
                rec.moodle_timeend and rec.moodle_timeend <= now
            ):
                rec.plataforma_estado = 'suspendido'
            else:
                rec.plataforma_estado = 'activo'
    plataforma_url = fields.Char(
        string='Perfil en la Plataforma', compute='_compute_plataforma_url',
        help="Enlace al perfil del estudiante en la Plataforma.",
    )

    @api.depends('moodle_user_id')
    def _compute_plataforma_url(self):
        client = self.env['moodle.client']
        try:
            config = self.env['moodle.config'].get_active_config()
        except UserError:
            config = False
        for rec in self:
            rec.plataforma_url = (
                client.get_profile_url(rec.moodle_user_id, config=config)
                if config and rec.moodle_user_id else False
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

    def _get_moodle_enrol_dates(self):
        """Devuelve (timestart, timeend) como timestamps para Moodle.

        Única fuente de la fórmula de vencimiento: fecha de vencimiento de
        la factura + 1 día (o hoy + 30 días si no hay factura).
        """
        self.ensure_one()
        timestart = (
            int(time.mktime(self.inscription_date.timetuple()))
            if self.inscription_date else int(time.time())
        )
        invoice_due_date = (
            self.move_id.invoice_date_due
            or (fields.Date.today() + timedelta(days=30))
        )
        expiry = invoice_due_date + timedelta(days=1)
        timeend = int(time.mktime(expiry.timetuple()))
        return timestart, timeend

    # ------------------------------------------------------------------
    # Resolución con caché: curso (IDs guardados en la Sección) y usuario
    # (ID ya vinculado al estudiante o a esta misma inscripción). Con todo
    # cacheado, action_sync_moodle no necesita buscar nada: solo matricula
    # y agrega al grupo (~2 peticiones en vez de las 6-8 originales).
    # ------------------------------------------------------------------
    def _moodle_resolve_course(self, client, config, code_moodle, force=False):
        self.ensure_one()
        standard = self.standard_id
        if not force and standard.moodle_course_id:
            return standard.moodle_course_id, standard.moodle_course_name or code_moodle, True

        course = client.search_course_by_shortname(
            code_moodle, config=config, related_record=self
        )
        if not course:
            raise UserError(_(
                "No se encontró un curso en Moodle con el código '%s'."
            ) % code_moodle)
        course_id = course.get('id')
        course_name = course.get('fullname') or course.get('shortname') or code_moodle
        standard.write({
            'moodle_course_id': course_id,
            'moodle_course_name': course_name,
        })
        return course_id, course_name, False

    def _moodle_resolve_user(self, client, config, user_vals, username, email, force=False):
        """Devuelve (moodle_user_id, desde_cache). El perfil (nombres,
        email, ciudad, país) solo se reenvía a Moodle cuando hace falta
        buscar o crear el usuario: las actualizaciones reactivas de
        nombre/email ya las cubre student.student.write() (ver
        student_inherit.py), así que repetirlas aquí en cada inscripción
        sería una petición redundante."""
        self.ensure_one()
        student = self.student_id
        if not force:
            cached = student.moodle_user_id or self.moodle_user_id
            if cached:
                return cached, True

        user = client.get_user_by_field(
            'username', username, config=config, related_record=self
        )
        if not user:
            user = client.get_user_by_field(
                'email', email, config=config, related_record=self
            )

        if user:
            moodle_user_id = user.get('id')
            client.update_user(
                {**user_vals, 'id': moodle_user_id},
                config=config, related_record=self,
            )
        else:
            # La contraseña por defecto solo se envía al CREAR: al
            # actualizar se pisaría la clave real del estudiante.
            user_vals = dict(user_vals, username=username, auth='manual',
                              password=config.default_password)
            moodle_user_id = client.create_user(
                user_vals, config=config, related_record=self
            )

        if not moodle_user_id:
            raise UserError(_(
                "No se pudo obtener ni generar el ID del usuario en Moodle."
            ))
        if not student.moodle_user_id:
            student.write({'moodle_user_id': moodle_user_id, 'moodle_synced': True})
        return moodle_user_id, False

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

            # ---------- 1. Curso en Moodle (usa el ID guardado en la Sección) ----------
            code_moodle = record.standard_id.subject_id.code_moodle
            if not code_moodle:
                raise UserError(_(
                    "El curso '%s' no tiene asignado un 'Código Moodle'.\n"
                    "Configure el campo 'Código Moodle' en el curso."
                ) % record.standard_id.subject_id.name)

            moodle_course_id, course_name, from_course_cache = \
                record._moodle_resolve_course(client, config, code_moodle)

            # ---------- 2. Usuario en Moodle (usa el ID ya vinculado) ----------
            user_vals = {
                'email': email,
                'firstname': firstname,
                'lastname': lastname,
                'city': config.default_city,
                'country': config.default_country,
            }
            moodle_user_id, from_user_cache = record._moodle_resolve_user(
                client, config, user_vals, username, email
            )

            # ---------- 3. Matrícula (si algo en caché quedó obsoleto, se
            #              releen una sola vez curso y/o usuario y se
            #              reintenta) ----------
            timestart, timeend = record._get_moodle_enrol_dates()
            try:
                client.enrol_user(
                    moodle_user_id, moodle_course_id, timestart, timeend,
                    role_id=config.enrol_role_id, config=config, related_record=record,
                )
            except UserError:
                if not (from_course_cache or from_user_cache):
                    raise
                if from_course_cache:
                    moodle_course_id, course_name, __ = record._moodle_resolve_course(
                        client, config, code_moodle, force=True
                    )
                if from_user_cache:
                    moodle_user_id, __ = record._moodle_resolve_user(
                        client, config, user_vals, username, email, force=True
                    )
                client.enrol_user(
                    moodle_user_id, moodle_course_id, timestart, timeend,
                    role_id=config.enrol_role_id, config=config, related_record=record,
                )
            # Solo se guarda si Moodle aceptó la matrícula (si falla,
            # enrol_user lanza excepción y no se llega aquí).
            record.moodle_course_id = moodle_course_id
            record.moodle_timeend = datetime.utcfromtimestamp(timeend)

            # ---------- 4. Grupo (sección dentro del curso, con ID guardado) ----------
            standard = record.standard_id
            group_code = standard.code
            if group_code:
                group_id = standard.moodle_group_id
                if not group_id:
                    group_id = client.get_or_create_group(
                        moodle_course_id, group_code,
                        config=config, related_record=record,
                    )
                    standard.moodle_group_id = group_id
                client.add_group_members(
                    group_id, moodle_user_id,
                    config=config, related_record=record,
                )
            else:
                record.message_post(body=_(
                    "Aviso: la sección '%s' no tiene configurado un "
                    "'Código de grupo Moodle'; el estudiante quedó "
                    "matriculado en el curso pero no se le asignó grupo."
                ) % record.standard_id.display_name)

            record.write({
                'moodle_enrolled': True,
                'moodle_user_id': moodle_user_id,
                'plataforma_curso': course_name,
                # enrol_user envía la matrícula sin 'suspend': la reactiva.
                'moodle_suspended': False,
                'moodle_sync_error': False,
                'moodle_error_message': False,
            })
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
