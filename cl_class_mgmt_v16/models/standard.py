# See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class SchoolStandard(models.Model):
    _inherit = 'school.standard'

    dias_clase_ids = fields.Many2many(
        'cl.dia.semana', string='Días de Clases',
        help='Días de la semana en que se dicta el curso')

    def _get_dias_seleccionados(self):
        """Índices de días de la semana (Lunes=0 ... Domingo=6) en que se dicta el curso."""
        self.ensure_one()
        return self.dias_clase_ids.mapped('weekday_index')

    def _calcular_fechas_clase(self, cantidad, fecha_inicio=None):
        """Calcula 'cantidad' de fechas a partir de 'fecha_inicio' (por
        defecto start_date de la sección), avanzando día a día y quedándose
        sólo con los días de la semana marcados en la sección."""
        self.ensure_one()

        fecha_inicio = fecha_inicio or self.start_date
        if not fecha_inicio:
            raise ValidationError(_(
                "La sección no tiene fecha de inicio configurada."))

        dias_semana = self._get_dias_seleccionados()
        if not dias_semana:
            raise ValidationError(_(
                "Debe seleccionar al menos un día de la semana en que se "
                "dicta el curso antes de iniciar la sección."))

        fechas = []
        fecha_actual = fecha_inicio
        tope = fecha_actual + timedelta(days=730)

        while len(fechas) < cantidad and fecha_actual <= tope:
            if fecha_actual.weekday() in dias_semana:
                fechas.append(fecha_actual)
            fecha_actual += timedelta(days=1)

        return fechas

    def _calcular_fecha_recomendada(self, cantidad, fecha_fin):
        """Última fecha de inicio posible para que, contando 'cantidad'
        fechas hacia adelante (según los días de clase), la última no
        exceda 'fecha_fin'. Se calcula retrocediendo día a día desde
        fecha_fin. Devuelve False si no hay suficientes días hábiles
        hacia atrás (en 2 años) para completar 'cantidad'."""
        self.ensure_one()

        dias_semana = self._get_dias_seleccionados()
        if not dias_semana or not fecha_fin or cantidad <= 0:
            return False

        fechas = []
        fecha_actual = fecha_fin
        tope = fecha_actual - timedelta(days=730)

        while len(fechas) < cantidad and fecha_actual >= tope:
            if fecha_actual.weekday() in dias_semana:
                fechas.append(fecha_actual)
            fecha_actual -= timedelta(days=1)

        return fechas[-1] if len(fechas) == cantidad else False

    #-----------------------------------------------------------------------#
    # PROVISIONAL: botón para recalcular fechas en secciones ya iniciadas,  #
    # antes de que existiera la automatización por días de clase. Eliminar #
    # este método y su botón en la vista una vez las secciones existentes  #
    # estén regularizadas.                                                 #
    #-----------------------------------------------------------------------#
    def action_recalcular_fechas_clase(self):
        for rec in self:
            asistencias = rec.asistencia_ids.sorted('id')
            if asistencias:
                fechas = rec._calcular_fechas_clase(len(asistencias))
                for asistencia, fecha in zip(asistencias, fechas):
                    asistencia.date_start = fecha

            evaluaciones = rec.registroeva_ids.sorted('id')
            for i, evaluacion in enumerate(evaluaciones, start=1):
                posicion = evaluacion._posicion_encuentro_evaluacion(i)
                fechas = rec._calcular_fechas_clase(posicion)
                evaluacion.date_start = fechas[-1]
