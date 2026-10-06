# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MoodleSyncLog(models.Model):
    """Auditoría de cada llamada al webservice de Moodle."""

    _name = 'moodle.sync.log'
    _description = 'Log de sincronización con Moodle'
    _order = 'create_date desc'

    name = fields.Char('Operación (wsfunction)', required=True)
    inscripcion_id = fields.Many2one(
        'student.inscripcion', 'Inscripción', ondelete='set null'
    )
    retiro_id = fields.Many2one(
        'student.retiro', 'Retiro', ondelete='set null'
    )
    cambio_id = fields.Many2one(
        'student.cambio', 'Cambio de Sección', ondelete='set null'
    )
    student_id = fields.Many2one(
        'student.student', 'Estudiante', ondelete='set null'
    )
    standard_id = fields.Many2one(
        'school.standard', 'Sección', ondelete='set null'
    )
    student_code = fields.Char('Código estudiante')
    status = fields.Selection(
        [('success', 'Éxito'), ('error', 'Error')],
        required=True, default='success',
    )
    message = fields.Text('Detalle / Error')
    request_data = fields.Text('Datos enviados', readonly=True)
    response_data = fields.Text('Respuesta de Moodle', readonly=True)
