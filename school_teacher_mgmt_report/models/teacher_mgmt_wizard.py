# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class TeacherMgmtWizard(models.TransientModel):
    _name = 'teacher.mgmt.wizard'
    _description = 'Wizard para generar reporte de Gestión Docente'

    # --- Filtros del Wizard ---
    teacher_id = fields.Many2one(
        'school.teacher',
        string='Profesor',
        help='Filtrar el reporte por un profesor específico.'
    )
    section_code = fields.Char(
        string='Código de Sección',
        help='Filtrar el reporte por el código de la sección.'
    )
    
    # Fecha de emisión (se usará en el reporte)
    date_today = fields.Date(
        'Fecha de Emisión',
        default=fields.Date.today,
        readonly=True
    )

    def _get_domain(self):
        """
        Construye el dominio para filtrar los registros de school.standard.
        """
        domain = []
        # Excluir secciones que están en estado 'cancel'
        domain.append(('state', '!=', 'cancel'))

        if self.teacher_id:
            domain.append(('user_id', '=', self.teacher_id.id))
        if self.section_code:
            domain.append(('code', '=', self.section_code.upper()))

        # Agregar filtro por compañía actual
        if self.env.user.company_id:
            domain.append(('company_id', '=', self.env.user.company_id.id))

        return domain

    def _get_report_data(self):
        """
        Obtiene los datos para el reporte.
        """
        domain = self._get_domain()
        # Buscar las secciones que cumplen con el dominio
        sections = self.env['school.standard'].search(domain)
        _logger.info(f"Se encontraron {len(sections)} secciones para el reporte.")

        # Estructurar los datos para el reporte
        data = {
            'sections': sections,
            'current_date': self.date_today or fields.Date.today(),
            'filters': {
                'teacher': self.teacher_id.name if self.teacher_id else 'Todos',
                'section_code': self.section_code if self.section_code else 'Todas',
            },
            'total_sections': len(sections),
            'company': self.env.user.company_id,
        }
        return data

    def generate_report(self):
        """
        Acción para generar y descargar el reporte PDF.
        """
        self.ensure_one()
        # Obtener los datos del reporte
        data = self._get_report_data()

        # Verificar que hay datos para mostrar
        if not data['sections']:
            raise ValidationError(_('No se encontraron secciones con los filtros seleccionados.'))

        # Devolver la acción para imprimir el reporte
        return self.env.ref('school_teacher_mgmt_report.report_teacher_mgmt_action').report_action(self, data=data)