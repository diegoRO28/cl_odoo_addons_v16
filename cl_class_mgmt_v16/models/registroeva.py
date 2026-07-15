# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StandardEvaluacion(models.Model):
    _inherit = 'standard.evaluacion'

    dias_diferencia_fin = fields.Integer(
        string='Días más allá del fin de curso',
        compute='_compute_dias_diferencia_fin', store=True,
        help='Días que la fecha de la evaluación excede la fecha de '
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
        sección (school.standard). Enganchado en create() -y no en
        generate_registroEva()- porque el módulo school_mod sobrescribe
        generate_registroEva sin llamar a super(), lo que impedía que un
        override a ese método se ejecutara de forma confiable."""
        for rec in self:
            if not rec.standard_id:
                continue
            cantidad = self.search_count(
                [('standard_id', '=', rec.standard_id.id)])
            posicion = rec._posicion_encuentro_evaluacion(cantidad)
            fechas = rec.standard_id._calcular_fechas_clase(posicion)
            rec.date_start = fechas[-1]

    def _posicion_encuentro_evaluacion(self, cantidad):
        """Traduce 'cantidad' (la evaluación Nro. cantidad de la sección,
        contada entre evaluaciones) a la posición real que le corresponde
        dentro del plan de encuentros del curso (subject.encuentros),
        tomando el encuentro Nro. 'cantidad' marcado como es_evaluacion.

        Si el plan del curso todavía no tiene encuentros marcados como
        evaluación (o tiene menos de los necesarios porque no ha sido
        migrado), se conserva el comportamiento anterior -contar sólo
        entre evaluaciones- para no romper secciones ya en curso."""
        self.ensure_one()
        encuentros = self.standard_id.subject_id.encuentro_ids
        encuentros_evaluacion = encuentros.filtered('es_evaluacion')
        if encuentros_evaluacion and cantidad <= len(encuentros_evaluacion):
            encuentro = encuentros_evaluacion[cantidad - 1]
            return encuentros.ids.index(encuentro.id) + 1
        return cantidad

    def _encuentro_evaluacion_correspondiente(self):
        """Devuelve el subject.encuentros (marcado es_evaluacion) que le
        corresponde a esta evaluación, según su posición entre las
        evaluaciones de la misma sección. Se usa para sincronizar la fecha
        de la evaluación con la fecha real del encuentro (incluso si ese
        encuentro fue reprogramado manualmente y ya no sigue la secuencia
        pura de _calcular_fechas_clase)."""
        self.ensure_one()
        siblings = self.standard_id.registroeva_ids.sorted('id')
        if self.id not in siblings.ids:
            return self.env['subject.encuentros']
        cantidad = siblings.ids.index(self.id) + 1
        encuentros_evaluacion = \
            self.standard_id.subject_id.encuentro_ids.filtered('es_evaluacion')
        if encuentros_evaluacion and cantidad <= len(encuentros_evaluacion):
            return encuentros_evaluacion[cantidad - 1]
        return self.env['subject.encuentros']
