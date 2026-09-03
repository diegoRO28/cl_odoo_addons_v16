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
    esa orquestación vive en inscripcion_inherit.py.
    """

    _name = 'moodle.client'
    _description = 'Cliente REST de Moodle'

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------
    def _log(self, name, status, message='', request_data=None,
              response_data=None, inscripcion=None):
        self.env['moodle.sync.log'].sudo().create({
            'name': name,
            'status': status,
            'message': message or '',
            'request_data': json.dumps(request_data, ensure_ascii=False, default=str)
            if request_data else False,
            'response_data': json.dumps(response_data, ensure_ascii=False, default=str)
            if response_data else False,
            'inscripcion_id': inscripcion.id if inscripcion else False,
            'student_code': inscripcion.student_code if inscripcion else False,
        })

    def _request(self, config, wsfunction, params=None, data=None,
                 method='GET', inscripcion=None):
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
                       inscripcion=inscripcion)
            raise UserError(_("Error de conexión con Moodle (%s): %s") % (wsfunction, e))

        text = response.text
        if not text or text.strip() == 'null':
            self._log(wsfunction, 'success', request_data=data or params,
                       inscripcion=inscripcion)
            return None

        try:
            result = json.loads(text)
        except ValueError:
            self._log(wsfunction, 'error', 'Respuesta no-JSON de Moodle',
                       request_data=data or params, response_data=text,
                       inscripcion=inscripcion)
            raise UserError(_("Moodle devolvió una respuesta inesperada para %s.") % wsfunction)

        if isinstance(result, dict) and result.get('exception'):
            self._log(wsfunction, 'error', result.get('message'),
                       request_data=data or params, response_data=result,
                       inscripcion=inscripcion)
            raise UserError(_("Moodle (%s): %s") % (wsfunction, result.get('message')))

        self._log(wsfunction, 'success', request_data=data or params,
                   response_data=result, inscripcion=inscripcion)
        return result

    # ------------------------------------------------------------------
    # Operaciones de alto nivel usadas por inscripcion_inherit.py
    # ------------------------------------------------------------------
    def get_site_info(self, config=None):
        config = config or self.env['moodle.config'].get_active_config()
        return self._request(config, 'core_webservice_get_site_info')

    def search_course_by_shortname(self, shortname, config=None, inscripcion=None):
        config = config or self.env['moodle.config'].get_active_config()
        result = self._request(
            config, 'core_course_get_courses_by_field',
            params={'field': 'shortname', 'value': shortname},
            inscripcion=inscripcion,
        )
        courses = (result or {}).get('courses', [])
        return courses[0] if courses else None

    def get_user_by_field(self, field, value, config=None, inscripcion=None):
        config = config or self.env['moodle.config'].get_active_config()
        result = self._request(
            config, 'core_user_get_users_by_field',
            params={'field': field, 'values[0]': value},
            inscripcion=inscripcion,
        )
        if isinstance(result, list) and result:
            return result[0]
        return None

    def create_user(self, vals, config=None, inscripcion=None):
        config = config or self.env['moodle.config'].get_active_config()
        data = {f'users[0][{k}]': v for k, v in vals.items()}
        result = self._request(config, 'core_user_create_users', data=data,
                                method='POST', inscripcion=inscripcion)
        if isinstance(result, list) and result:
            return result[0].get('id')
        return None

    def update_user(self, vals, config=None, inscripcion=None):
        config = config or self.env['moodle.config'].get_active_config()
        data = {f'users[0][{k}]': v for k, v in vals.items()}
        self._request(config, 'core_user_update_users', data=data,
                       method='POST', inscripcion=inscripcion)
        return vals.get('id')

    def enrol_user(self, user_id, course_id, timestart, timeend, role_id=None,
                    config=None, inscripcion=None):
        config = config or self.env['moodle.config'].get_active_config()
        data = {
            'enrolments[0][roleid]': role_id or config.enrol_role_id,
            'enrolments[0][userid]': user_id,
            'enrolments[0][courseid]': course_id,
            'enrolments[0][timestart]': timestart,
            'enrolments[0][timeend]': timeend,
        }
        self._request(config, 'enrol_manual_enrol_users', data=data,
                       method='POST', inscripcion=inscripcion)
        return True
