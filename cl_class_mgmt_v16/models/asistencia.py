# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SubjectAsistencia(models.Model):
    _inherit = 'subject.asistencia'

    dias_diferencia_fin = fields.Integer(
        string='Días más allá del fin de curso',
        compute='_compute_dias_diferencia_fin', store=True,
        help='Días que la fecha del encuentro excede la fecha de '
             'finalización de la sección (0 si está dentro del período).')

    reprogramando = fields.Boolean(
        string='Reprogramando', default=False, copy=False,
        help='Mientras esté marcado, la Fecha de inicio queda editable. '
             'Se pone en False automáticamente al guardar.')

    def action_reprogramar(self):
        self.write({'reprogramando': True})

    def write(self, vals):
        res = super().write(vals)
        if 'reprogramando' not in vals:
            self.filtered('reprogramando').write({'reprogramando': False})
        return res

    @api.depends('date_start', 'standard_id.end_date')
    def _compute_dias_diferencia_fin(self):
        for rec in self:
            if rec.date_start and rec.standard_id.end_date and \
                    rec.date_start > rec.standard_id.end_date:
                rec.dias_diferencia_fin = (rec.date_start - rec.standard_id.end_date).days
            else:
                rec.dias_diferencia_fin = 0

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._asignar_fecha_automatica()
        return rec

    def _asignar_fecha_automatica(self):
        """Calcula date_start según el día de la semana configurado en la
        sección (school.standard), en vez de dejar el default 'hoy'.

        Se engancha en create() -en lugar de en generate_encuentros()- porque
        el módulo school_mod también sobrescribe métodos relacionados en
        school.standard sin llamar a super(), lo que impedía que un override
        de generate_encuentros/generate_registroEva se ejecutara de forma
        confiable."""
        for rec in self:
            if not rec.standard_id:
                continue
            cantidad = self.search_count(
                [('standard_id', '=', rec.standard_id.id)])
            fechas = rec.standard_id._calcular_fechas_clase(cantidad)
            rec.date_start = fechas[-1]
