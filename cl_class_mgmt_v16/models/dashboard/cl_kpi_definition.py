# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ClKpiDefinition(models.Model):
    _name = 'cl.kpi.definition'
    _description = 'Definición de KPI configurable'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True)
    technical_key = fields.Char(
        string='Clave técnica', required=True,
        help="Clave que el componente OWL usa para buscar este KPI en el "
             "dict de datos devuelto por get_dashboard_data(). Ej: "
             "'pct_asistencias_al_dia', 'total_estudiantes', 'retiros_mes'.")
    dashboard_model = fields.Char(
        string='Modelo de dashboard',
        help="Nombre técnico (_name) del modelo de dashboard al que "
             "pertenece este KPI. Ej: 'cl.academic.dashboard'. No es una "
             "relación Many2one: cada dashboard concreto busca sus propios "
             "KPIs filtrando por este valor (ver "
             "cl.dashboard.config._get_kpi_definitions).")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    default_viz = fields.Selection([
        ('number', 'Número grande'),
        ('bar', 'Barras'),
        ('donut', 'Donut'),
        ('line', 'Línea de tendencia'),
        ('table', 'Tabla'),
    ], string='Visualización por defecto', default='number')
    allow_viz = fields.Char(
        string='Visualizaciones permitidas',
        help="CSV de las claves de visualización habilitadas para este "
             "KPI, ej. 'number,bar,donut'. El componente OWL lo usa para "
             "mostrar los botones de cambio de vista.")
    color_theme = fields.Selection([
        ('blue', 'Azul'),
        ('teal', 'Verde'),
        ('amber', 'Ámbar'),
        ('coral', 'Coral'),
        ('purple', 'Morado'),
    ], string='Color', default='blue')
    description = fields.Text(string='Descripción para el usuario')
