# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ClTeacherKpiSnapshot(models.Model):
    _name = 'cl.teacher.kpi.snapshot'
    _description = 'Histórico diario de % de carga (asistencias/notas) del panel docente'
    _order = 'date asc'

    date = fields.Date(required=True, index=True, default=fields.Date.context_today)
    pct_asistencias = fields.Integer('% carga de asistencias', required=True)
    pct_evaluaciones = fields.Integer('% carga de notas', required=True)

    _sql_constraints = [
        ('date_uniq', 'unique(date)', 'Ya existe un snapshot para esta fecha.'),
    ]

    @api.model
    def _get_or_create_today(self, pct_asistencias, pct_evaluaciones):
        """Un snapshot por día -- si el panel se abre varias veces el mismo
        día, se actualiza el valor (queda el más reciente del día), no se
        duplica la fila."""
        hoy = fields.Date.context_today(self)
        rec = self.search([('date', '=', hoy)], limit=1)
        vals = {'pct_asistencias': pct_asistencias, 'pct_evaluaciones': pct_evaluaciones}
        if rec:
            rec.write(vals)
            return rec
        vals['date'] = hoy
        return self.create(vals)

    @api.model
    def get_history(self, kind, limit=30):
        """kind: 'asistencias' o 'evaluaciones'. Devuelve los últimos
        'limit' días disponibles, en orden cronológico ascendente. Público
        (sin '_') porque se llama vía RPC desde el componente OWL."""
        field_name = 'pct_asistencias' if kind == 'asistencias' else 'pct_evaluaciones'
        recs = self.search([], order='date desc', limit=limit)
        return [{'date': r.date.strftime('%d/%m/%Y'), 'value': r[field_name]} for r in reversed(recs)]

    @api.model
    def _cron_capture_today(self):
        """Ejecutado diariamente por ir.cron -- garantiza que quede un
        snapshot aunque nadie abra el panel docente ese día."""
        data = self.env['teacher.mgmt.wizard'].get_dashboard_data()
        self._get_or_create_today(data['global_percentage'], data['global_eval_percentage'])
