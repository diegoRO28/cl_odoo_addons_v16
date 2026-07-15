# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ClDiaSemana(models.Model):
    _name = 'cl.dia.semana'
    _description = 'Día de la semana (para configurar días de clase)'
    _order = 'sequence'

    name = fields.Char('Día', required=True)
    sequence = fields.Integer('Secuencia', required=True)
    weekday_index = fields.Integer(
        'Índice', required=True,
        help='Lunes=0 ... Domingo=6, según date.weekday() de Python')
    color = fields.Integer('Color')
