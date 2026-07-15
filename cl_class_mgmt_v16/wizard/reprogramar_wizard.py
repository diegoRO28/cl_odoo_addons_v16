# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class SchoolStandardReprogramarWizard(models.TransientModel):
    _name = 'school.standard.reprogramar.wizard'
    _description = 'Reprogramar encuentros/evaluaciones de una sección'

    standard_id = fields.Many2one(
        'school.standard', string='Sección', required=True,
        default=lambda self: self.env.context.get('active_id'))

    tipo = fields.Selection([
        ('encuentro', 'Encuentros'),
        ('evaluacion', 'Evaluaciones'),
        ('ambos', 'Ambos'),
    ], string='¿Qué se va a reprogramar?', required=True, default='ambos')

    nueva_fecha = fields.Date(
        string='Fecha del próximo encuentro',
        help='A partir de esta fecha se recalculan los encuentros/'
             'evaluaciones pendientes (los ya dictados/evaluados no se '
             'tocan), siguiendo los Días de Clases configurados en la '
             'sección.')

    ultima_asistencia_info = fields.Char(
        string='Última asistencia cargada', compute='_compute_info', readonly=True)
    fecha_ultima_asistencia = fields.Date(
        string='Fecha de la última asistencia', compute='_compute_info', readonly=True)

    ultima_evaluacion_info = fields.Char(
        string='Última evaluación cargada', compute='_compute_info', readonly=True)
    fecha_ultima_evaluacion = fields.Date(
        string='Fecha de la última evaluación', compute='_compute_info', readonly=True)

    @staticmethod
    def _concatenar(*partes):
        partes = [p for p in partes if p]
        return ' - '.join(partes) if partes else False

    @api.depends('standard_id')
    def _compute_info(self):
        for rec in self:
            standard = rec.standard_id

            asistencias_cargadas = standard.asistencia_ids.filtered(
                lambda a: a.state != 'draft').sorted('id')
            ultima_asistencia = asistencias_cargadas[-1:]
            rec.ultima_asistencia_info = rec._concatenar(
                ultima_asistencia.encuentro_id.name, ultima_asistencia.note)
            rec.fecha_ultima_asistencia = ultima_asistencia.date_start if ultima_asistencia else False

            evaluaciones_cargadas = standard.registroeva_ids.filtered(
                lambda e: e.state != 'draft').sorted('id')
            ultima_evaluacion = evaluaciones_cargadas[-1:]
            rec.ultima_evaluacion_info = rec._concatenar(
                ultima_evaluacion.nombre, ultima_evaluacion.note)
            rec.fecha_ultima_evaluacion = ultima_evaluacion.date_start if ultima_evaluacion else False

    def _validar_no_excede_fin(self, standard, cantidad):
        """Verifica que reprogramar 'cantidad' fechas desde nueva_fecha no
        exceda standard.end_date. Si excede, corta con un error que incluye
        una fecha recomendada, en vez de ajustar la fecha automáticamente."""
        self.ensure_one()
        if not standard.end_date or not cantidad:
            return

        fechas = standard._calcular_fechas_clase(cantidad, fecha_inicio=self.nueva_fecha)
        if not fechas or fechas[-1] <= standard.end_date:
            return

        recomendada = standard._calcular_fecha_recomendada(cantidad, standard.end_date)
        if recomendada:
            raise ValidationError(_(
                "La fecha elegida (%(fecha)s) hace que la reprogramación "
                "termine el %(ultima)s, después del fin de curso "
                "(%(fin_curso)s).\n\n"
                "Fecha recomendada para que la reprogramación entre antes "
                "del fin de curso: %(recomendada)s. Ajústela manualmente "
                "y vuelva a intentar."
            ) % {
                'fecha': self.nueva_fecha,
                'ultima': fechas[-1],
                'fin_curso': standard.end_date,
                'recomendada': recomendada,
            })
        raise ValidationError(_(
            "No hay suficientes días de clase entre la fecha elegida y el "
            "fin de curso (%s) para reprogramar los %s encuentros/"
            "evaluaciones pendientes."
        ) % (standard.end_date, cantidad))

    def action_confirmar(self):
        self.ensure_one()
        standard = self.standard_id

        if self.tipo in ('encuentro', 'ambos') and not self.nueva_fecha:
            raise ValidationError(_(
                "Debe indicar la fecha del próximo encuentro."))

        pendientes_asis = standard.asistencia_ids.filtered(
            lambda a: a.state == 'draft').sorted('id')
        pendientes_eva = standard.registroeva_ids.filtered(
            lambda e: e.state == 'draft').sorted('id')

        if self.tipo in ('encuentro', 'ambos') and pendientes_asis:
            self._validar_no_excede_fin(standard, len(pendientes_asis))

        # Evaluaciones pendientes que no tienen un encuentro es_evaluacion
        # vinculado (curso sin migrar): su fecha se calcula de forma
        # independiente y también debe validarse contra end_date.
        pendientes_eva_sin_encuentro = pendientes_eva.filtered(
            lambda e: not e._encuentro_evaluacion_correspondiente())
        if self.tipo in ('evaluacion', 'ambos') and self.nueva_fecha \
                and pendientes_eva_sin_encuentro:
            self._validar_no_excede_fin(standard, len(pendientes_eva_sin_encuentro))

        if self.tipo in ('encuentro', 'ambos') and pendientes_asis:
            fechas = standard._calcular_fechas_clase(
                len(pendientes_asis), fecha_inicio=self.nueva_fecha)
            for asistencia, fecha in zip(pendientes_asis, fechas):
                asistencia.date_start = fecha

        if self.tipo in ('evaluacion', 'ambos'):
            i = 0
            for evaluacion in pendientes_eva:
                encuentro = evaluacion._encuentro_evaluacion_correspondiente()
                asistencia = encuentro and standard.asistencia_ids.filtered(
                    lambda a, enc=encuentro: a.encuentro_id == enc)
                if asistencia:
                    evaluacion.date_start = asistencia[0].date_start
                elif self.nueva_fecha:
                    i += 1
                    fechas = standard._calcular_fechas_clase(
                        i, fecha_inicio=self.nueva_fecha)
                    evaluacion.date_start = fechas[-1]

        return {'type': 'ir.actions.act_window_close'}
