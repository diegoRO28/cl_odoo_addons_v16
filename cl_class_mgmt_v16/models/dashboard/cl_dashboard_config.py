# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ClDashboardConfig(models.AbstractModel):
    _name = 'cl.dashboard.config'
    _description = 'Configuración base de dashboard'

    user_id = fields.Many2one(
        'res.users', string='Usuario', default=lambda self: self.env.user,
        required=True)
    campus_ids = fields.Many2many('school.campus', string='Campus')
    date_from = fields.Date(string='Desde')
    date_to = fields.Date(string='Hasta')
    period_mode = fields.Selection([
        ('month', 'Último mes'),
        ('quarter', 'Último trimestre'),
        ('semester', 'Último semestre'),
        ('year', 'Todo el año'),
        ('custom', 'Personalizado'),
    ], string='Período', default='month')

    def _get_kpi_definitions(self):
        """KPIs configurados para este dashboard: cl.kpi.definition cuyo
        dashboard_model coincide con el _name del modelo concreto que
        hereda de este abstracto (cl.academic.dashboard, cl.teacher.dashboard,
        cl.admin.dashboard...). No es un One2many real porque
        dashboard_model es un Char (etiqueta), no un Many2one, y un
        AbstractModel no tiene tabla propia para ser destino de una
        relación inversa."""
        return self.env['cl.kpi.definition'].search(
            [('dashboard_model', '=', self._name)])
