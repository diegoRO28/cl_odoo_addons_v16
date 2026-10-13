# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _


class MoodleConfig(models.Model):
    """Configuración de conexión a un sitio Moodle, POR EMPRESA.

    Reemplaza los valores que antes estaban hardcodeados en
    inscripcion.py (moodle_url, moodle_token, password por defecto, etc).

    Cada empresa (res.company) tiene su propia configuración: su URL y su
    token apuntan al aula virtual de esa empresa. Para cada empresa solo
    puede haber UNA configuración activa, y esa es la que se usa cuando se
    trabaja con esa empresa.
    """

    _name = 'moodle.config'
    _description = 'Configuración de conexión a Moodle'
    _rec_name = 'name'

    company_id = fields.Many2one(
        'res.company', string='Empresa', required=True,
        default=lambda self: self.env.company, ondelete='cascade',
        help="Empresa a la que pertenece esta configuración. Cada empresa "
             "se conecta a su propia aula virtual (su propia URL y token).",
    )
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
        'País por defecto', default='VE',
        help="Código ISO de 2 letras (ej. VE), NO el nombre completo: "
             "Moodle rechaza el nombre con 'Invalid parameter value'.",
    )
    enrol_role_id = fields.Integer('Role ID de matrícula', default=5)
    timeout = fields.Integer('Timeout (segundos)', default=10)
    active = fields.Boolean('Activo', default=True)

    # Misma clave 'unique_config_name', definición nueva: Odoo detecta que
    # cambió y reemplaza la restricción existente al actualizar el módulo.
    _sql_constraints = [
        ('unique_config_name', 'unique(name, company_id)',
         'Ya existe una configuración con ese nombre para esta empresa.'),
    ]

    @api.constrains('active', 'company_id')
    def _check_one_active_per_company(self):
        """Una sola configuración activa por empresa: get_active_config()
        toma la primera que encuentra, y dos activas serían ambiguas."""
        for rec in self.filtered('active'):
            # sudo: la comprobación de integridad debe ver todo, sin
            # importar qué empresas tenga seleccionadas el usuario.
            others = self.sudo().search_count([
                ('company_id', '=', rec.company_id.id),
                ('active', '=', True),
                ('id', '!=', rec.id),
            ])
            if others:
                raise ValidationError(_(
                    "La empresa '%s' ya tiene una configuración activa. "
                    "Archive o desactive la anterior antes de activar esta."
                ) % rec.company_id.display_name)

    @api.model
    def get_active_config(self, company=None):
        """Devuelve la configuración activa de una empresa o lanza un error.

        company: res.company (o su id). Si no se indica, se usa la empresa
        actual del usuario (la seleccionada en el selector de empresas).
        """
        if company and not isinstance(company, models.BaseModel):
            company = self.env['res.company'].browse(company)
        company = company or self.env.company
        config = self.search([
            ('active', '=', True),
            ('company_id', '=', company.id),
        ], limit=1)
        if not config:
            raise UserError(_(
                "No hay una configuración activa para la empresa '%s'.\n"
                "Vaya a Class > Plataforma > Configuración > Conexión y "
                "cree una para esa empresa, con la URL de su aula virtual "
                "y el token de acceso."
            ) % company.display_name)
        return config

    def action_test_connection(self):
        """Botón 'Probar conexión': llama a core_webservice_get_site_info."""
        self.ensure_one()
        info = self.env['moodle.client'].get_site_info(config=self) or {}
        message = _("Empresa: %s — Sitio: %s — Release: %s") % (
            self.company_id.display_name,
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
