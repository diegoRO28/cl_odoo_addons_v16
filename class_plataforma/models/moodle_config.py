# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class MoodleConfig(models.Model):
    """Configuración de conexión a un sitio Moodle.

    Reemplaza los valores que antes estaban hardcodeados en
    inscripcion.py (moodle_url, moodle_token, password por defecto, etc).
    Se toma como config "activa" el primer registro con active=True.
    """

    _name = 'moodle.config'
    _description = 'Configuración de conexión a Moodle'
    _rec_name = 'name'

    name = fields.Char('Nombre', default='Configuración Moodle', required=True)
    url = fields.Char(
        'URL Webservice Moodle', required=True,
        help="Ej: http://localhost/webservice/rest/server.php "
             "(o la URL del túnel SSH que estés usando).",
    )
    token = fields.Char('Token', required=True)
    default_password = fields.Char('Password por defecto', default='1234')
    default_city = fields.Char('Ciudad por defecto', default='Acarigua')
    default_country = fields.Char(
        'País por defecto', default='Venezuela (Bolivarian Republic of)'
    )
    enrol_role_id = fields.Integer('Role ID de matrícula', default=5)
    timeout = fields.Integer('Timeout (segundos)', default=10)
    active = fields.Boolean('Activo', default=True)

    _sql_constraints = [
        ('unique_config_name', 'unique(name)',
         'Ya existe una configuración de Moodle con ese nombre.'),
    ]

    @api.model
    def get_active_config(self):
        """Devuelve la configuración activa o lanza un error claro."""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            raise UserError(_(
                "No hay una configuración activa de Moodle.\n"
                "Vaya a Moodle Connector > Configuración y cree una, "
                "con la URL del webservice y el token de acceso."
            ))
        return config

    def action_test_connection(self):
        """Botón 'Probar conexión': llama a core_webservice_get_site_info."""
        self.ensure_one()
        info = self.env['moodle.client'].get_site_info(config=self) or {}
        message = _("Sitio: %s — Release: %s") % (
            info.get('sitename', '?'), info.get('release', '?')
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Conexión con Moodle exitosa'),
                'message': message,
                'type': 'success',
                'sticky': False,
            },
        }
