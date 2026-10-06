# See LICENSE file for full copyright and licensing details.

import json
import logging
import urllib.parse

import requests

from odoo import models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class MoodleClient(models.AbstractModel):
    """Cliente REST de Moodle (Web Services).

    Solo sabe hablar HTTP con Moodle y dejar constancia en
    moodle.sync.log. No conoce 'student.inscripcion' ni nada de 'school':
    esa orquestación vive en los *_inherit.py de cada modelo.
    """

    _name = 'moodle.client'
    _description = 'Cliente REST de Moodle'

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------
    def _log(self, name, status, message='', request_data=None,
              response_data=None, related_record=None, student_code=None):
        """related_record puede ser un student.inscripcion, student.retiro,
        student.cambio, student.student o school.standard (o None). Se enlaza
        al campo Many2one correcto según su modelo real, para no escribir un ID
        en el campo equivocado."""
        code = student_code or getattr(related_record, 'student_code', False)
        vals = {
            'name': name,
            'status': status,
            'message': message or '',
            'request_data': json.dumps(request_data, ensure_ascii=False, default=str)
            if request_data else False,
            'response_data': json.dumps(response_data, ensure_ascii=False, default=str)
            if response_data else False,
            'student_code': code,
        }
        if related_record:
            model = related_record._name
            if model == 'student.inscripcion':
                vals['inscripcion_id'] = related_record.id
            elif model == 'student.retiro':
                vals['retiro_id'] = related_record.id
            elif model == 'student.cambio':
                vals['cambio_id'] = related_record.id
            elif model == 'student.student':
                vals['student_id'] = related_record.id
            elif model == 'school.standard':
                vals['standard_id'] = related_record.id
        self.env['moodle.sync.log'].sudo().create(vals)

    def _request(self, config, wsfunction, params=None, data=None,
                 method='GET', related_record=None, student_code=None):
        params = params or {}
        base_params = {
            'wstoken': config.token,
            'wsfunction': wsfunction,
            'moodlewsrestformat': 'json',
        }
        query = urllib.parse.urlencode({**base_params, **params})
        url = f"{config.url}?{query}"

        try:
            if method == 'GET':
                response = requests.get(url, timeout=config.timeout or 10)
            else:
                response = requests.post(url, data=data or {}, timeout=config.timeout or 10)
            response.raise_for_status()
        except requests.RequestException as e:
            self._log(wsfunction, 'error', str(e), request_data=data or params,
                       related_record=related_record, student_code=student_code)
            raise UserError(_("Error de conexión con Moodle (%s): %s") % (wsfunction, e))

        text = response.text
        if not text or text.strip() == 'null':
            self._log(wsfunction, 'success', request_data=data or params,
                       related_record=related_record, student_code=student_code)
            return None

        try:
            result = json.loads(text)
        except ValueError:
            self._log(wsfunction, 'error', 'Respuesta no-JSON de Moodle',
                       request_data=data or params, response_data=text,
                       related_record=related_record, student_code=student_code)
            raise UserError(_("Moodle devolvió una respuesta inesperada para %s.") % wsfunction)

        if isinstance(result, dict) and result.get('exception'):
            self._log(wsfunction, 'error', result.get('message'),
                       request_data=data or params, response_data=result,
                       related_record=related_record, student_code=student_code)
            raise UserError(_("Moodle (%s): %s") % (wsfunction, result.get('message')))

        self._log(wsfunction, 'success', request_data=data or params,
                   response_data=result, related_record=related_record,
                   student_code=student_code)
        return result

    # ------------------------------------------------------------------
    # Usuario / matrícula (Fase 0 — Inscripción)
    # ------------------------------------------------------------------
    def get_site_info(self, config=None):
        config = config or self.env['moodle.config'].get_active_config()
        return self._request(config, 'core_webservice_get_site_info')

    def search_course_by_shortname(self, shortname, config=None, related_record=None):
        config = config or self.env['moodle.config'].get_active_config()
        result = self._request(
            config, 'core_course_get_courses_by_field',
            params={'field': 'shortname', 'value': shortname},
            related_record=related_record,
        )
        courses = (result or {}).get('courses', [])
        return courses[0] if courses else None

    def get_user_by_field(self, field, value, config=None, related_record=None, student_code=None):
        config = config or self.env['moodle.config'].get_active_config()
        result = self._request(
            config, 'core_user_get_users_by_field',
            params={'field': field, 'values[0]': value},
            related_record=related_record,
            student_code=student_code,
        )
        if isinstance(result, list) and result:
            return result[0]
        return None

    def create_user(self, vals, config=None, related_record=None):
        config = config or self.env['moodle.config'].get_active_config()
        data = {f'users[0][{k}]': v for k, v in vals.items()}
        result = self._request(config, 'core_user_create_users', data=data,
                                method='POST', related_record=related_record)
        if isinstance(result, list) and result:
            return result[0].get('id')
        return None

    def update_user(self, vals, config=None, related_record=None):
        config = config or self.env['moodle.config'].get_active_config()
        data = {f'users[0][{k}]': v for k, v in vals.items()}
        self._request(config, 'core_user_update_users', data=data,
                       method='POST', related_record=related_record)
        return vals.get('id')

    def set_user_suspended(self, user_id, suspended=True, config=None, related_record=None):
        """Suspende (o reactiva) la CUENTA del usuario en todo el sitio
        (bloquea el login por completo). No se usa para Retiro — ver
        set_enrolment_suspended para suspender solo dentro de un curso."""
        config = config or self.env['moodle.config'].get_active_config()
        return self.update_user(
            {'id': user_id, 'suspended': 1 if suspended else 0},
            config=config, related_record=related_record,
        )

    def set_enrolment_suspended(self, user_id, course_id, timestart, timeend,
                                  role_id=None, suspended=True, config=None,
                                  related_record=None):
        """Cambia el estado de la matrícula (Activo/Suspendido) DENTRO de
        un curso específico, sin tocar la cuenta ni sacar al estudiante
        del curso. enrol_manual_enrol_users, llamado de nuevo sobre una
        matrícula que ya existe, actualiza sus datos (incluido el estado)
        en vez de crear una matrícula duplicada — por eso se reenvían
        también timestart/timeend, para no perder esos valores."""
        config = config or self.env['moodle.config'].get_active_config()
        data = {
            'enrolments[0][roleid]': role_id or config.enrol_role_id,
            'enrolments[0][userid]': user_id,
            'enrolments[0][courseid]': course_id,
            'enrolments[0][timestart]': timestart,
            'enrolments[0][timeend]': timeend,
            'enrolments[0][suspend]': 1 if suspended else 0,
        }
        self._request(config, 'enrol_manual_enrol_users', data=data,
                       method='POST', related_record=related_record)
        return True

    def enrol_user(self, user_id, course_id, timestart, timeend, role_id=None,
                    config=None, related_record=None, student_code=None):
        config = config or self.env['moodle.config'].get_active_config()
        data = {
            'enrolments[0][roleid]': role_id or config.enrol_role_id,
            'enrolments[0][userid]': user_id,
            'enrolments[0][courseid]': course_id,
            'enrolments[0][timestart]': timestart,
            'enrolments[0][timeend]': timeend,
        }
        self._request(config, 'enrol_manual_enrol_users', data=data,
                       method='POST', related_record=related_record,
                       student_code=student_code)
        return True

    def get_site_base_url(self, config=None):
        """URL base del sitio Moodle, derivada de la URL del webservice
        (config.url apunta a .../webservice/rest/server.php)."""
        config = config or self.env['moodle.config'].get_active_config()
        url = (config.url or '').strip()
        marker = '/webservice/'
        base = url.split(marker)[0] if marker in url else url
        return base.rstrip('/')

    def get_profile_url(self, user_id, config=None):
        """Enlace al perfil de un usuario en Moodle (o False si no hay ID)."""
        if not user_id:
            return False
        return "%s/user/profile.php?id=%s" % (self.get_site_base_url(config), user_id)

    def get_user_courses(self, user_id, config=None, related_record=None):
        """Cursos en los que el usuario está matriculado (verificación)."""
        config = config or self.env['moodle.config'].get_active_config()
        result = self._request(
            config, 'core_enrol_get_users_courses',
            params={'userid': user_id},
            related_record=related_record,
        )
        return result or []

    # ------------------------------------------------------------------
    # Grupos (Fase 2 — Retiro / Cambio de sección)
    # ------------------------------------------------------------------
    def get_course_groups(self, course_id, config=None, related_record=None):
        """Todos los grupos de un curso (para ubicar el grupo destino
        por nombre — Moodle no tiene una función de 'buscar grupo por
        nombre', hay que listar y filtrar del lado de Odoo)."""
        config = config or self.env['moodle.config'].get_active_config()
        result = self._request(
            config, 'core_group_get_course_groups',
            params={'courseid': course_id},
            related_record=related_record,
        )
        return result or []

    def get_user_groups_in_course(self, user_id, course_id, config=None, related_record=None):
        """Grupos a los que pertenece un usuario dentro de un curso
        específico (para verificar el grupo actual antes de moverlo)."""
        config = config or self.env['moodle.config'].get_active_config()
        result = self._request(
            config, 'core_group_get_course_user_groups',
            params={'courseid': course_id, 'userid': user_id},
            related_record=related_record,
        )
        if isinstance(result, dict):
            return result.get('groups', [])
        return result or []

    def add_group_members(self, group_id, user_id, config=None, related_record=None, student_code=None):
        config = config or self.env['moodle.config'].get_active_config()
        data = {
            'members[0][groupid]': group_id,
            'members[0][userid]': user_id,
        }
        self._request(config, 'core_group_add_group_members', data=data,
                       method='POST', related_record=related_record,
                       student_code=student_code)
        return True

    def remove_group_members(self, group_id, user_id, config=None, related_record=None):
        config = config or self.env['moodle.config'].get_active_config()
        data = {
            'members[0][groupid]': group_id,
            'members[0][userid]': user_id,
        }
        self._request(config, 'core_group_delete_group_members', data=data,
                       method='POST', related_record=related_record)
        return True

    def create_group(self, course_id, name, config=None, related_record=None):
        """Crea un grupo nuevo en el curso, solo con 'name' (igual que al
        crearlo manualmente en Moodle — el 'idnumber' es opcional ahí y
        no lo usamos)."""
        config = config or self.env['moodle.config'].get_active_config()
        data = {
            'groups[0][courseid]': course_id,
            'groups[0][name]': name,
            'groups[0][description]': '',
            'groups[0][descriptionformat]': 1,
        }
        result = self._request(config, 'core_group_create_groups', data=data,
                                method='POST', related_record=related_record)
        if isinstance(result, list) and result:
            return result[0].get('id')
        return None

    def get_or_create_group(self, course_id, group_name, config=None, related_record=None):
        """Busca un grupo del curso por 'name' (el código/nombre de la
        sección en Odoo). Si no existe todavía en Moodle, lo crea."""
        groups = self.get_course_groups(
            course_id, config=config, related_record=related_record
        ) or []
        match = next(
            (g for g in groups if g.get('name') == group_name), None
        )
        if match:
            return match.get('id')
        return self.create_group(
            course_id, group_name,
            config=config, related_record=related_record,
        )
